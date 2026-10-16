from datetime import datetime
import flet as ft
from config.settings import CURRENCY_SYMBOL, EXPENSE_CATEGORIES, INCOME_CATEGORIES
from ui.components.auth_modal import AuthModal
from ui.components.calendar_history import MONTH_FULL_NAMES, WEEKDAYS_ES, build_interactive_calendar
from ui.components.charts import (
    build_budget_50_30_20_card,
    build_cashflow_bar_chart,
    build_expense_pie_chart,
)
from ui.components.quick_modal import TransactionModal, parse_payment_and_note
from ui.components.summary_cards import build_summary_cards

MONTH_NAMES = {
    1: "Ene",
    2: "Feb",
    3: "Mar",
    4: "Abr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Ago",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dic",
}


class DashboardView:
    def __init__(self, page: ft.Page, local_storage, supabase_service):
        self.page = page
        self.local_storage = local_storage
        self.supabase_service = supabase_service

        now = datetime.now()
        self.current_year: int = now.year
        self.current_month: int = now.month
        self.selected_day: int | None = None
        self.active_tab: int = 0  # 0 = Resumen, 1 = Calendario e Historial
        self.history_filter_type: str = "todos"  # "todos", "gasto", "ingreso"
        self.search_query: str = ""

        self.main_column = ft.Column(spacing=14, scroll=ft.ScrollMode.HIDDEN, expand=True)
        self.modal = TransactionModal(self.page, self.handle_save_transaction)
        self.auth_modal = AuthModal(self.page, self.supabase_service, self._on_auth_changed)

        self.auth_button = ft.FilledTonalButton(
            "Cuenta",
            icon=ft.Icons.ACCOUNT_CIRCLE,
            style=ft.ButtonStyle(padding=ft.padding.symmetric(horizontal=10, vertical=4)),
            on_click=lambda e: self.auth_modal.open(),
        )

        self.search_input = ft.TextField(
            hint_text="Buscar por nota, categoría o método...",
            prefix_icon=ft.Icons.SEARCH,
            border_radius=12,
            text_size=13,
            height=42,
            content_padding=ft.padding.symmetric(horizontal=12, vertical=8),
            on_change=self._on_search_change,
        )

        # Estado y diálogo de confirmación antes de borrar
        self.tx_to_delete: dict | None = None
        self.delete_warning_text = ft.Text("", size=13)
        self.confirm_delete_dialog = ft.AlertDialog(
            modal=True,
            inset_padding=ft.padding.symmetric(horizontal=16, vertical=20),
            title=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color="red400"),
                    ft.Text("Confirmar eliminación", weight=ft.FontWeight.BOLD, size=16),
                ],
            ),
            content=self.delete_warning_text,
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.page.close(self.confirm_delete_dialog)),
                ft.FilledButton(
                    "Eliminar",
                    icon=ft.Icons.DELETE_FOREVER,
                    bgcolor="red400",
                    color="white",
                    on_click=self._confirm_delete_execution,
                ),
            ],
        )

        self.nav_bar = ft.NavigationBar(
            selected_index=0,
            height=62,
            on_change=self._on_tab_change,
            destinations=[
                ft.NavigationBarDestination(
                    icon=ft.Icons.DASHBOARD_OUTLINED,
                    selected_icon=ft.Icons.DASHBOARD,
                    label="Resumen",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.CALENDAR_MONTH_OUTLINED,
                    selected_icon=ft.Icons.CALENDAR_MONTH,
                    label="Calendario e Historial",
                ),
            ],
        )

    # --- Navegación de Meses y Pestañas ---
    def _on_tab_change(self, e):
        self.active_tab = e.control.selected_index
        self.refresh_ui()

    def switch_to_tab(self, idx: int):
        self.active_tab = idx
        self.nav_bar.selected_index = idx
        self.refresh_ui()

    def _prev_month(self, e=None):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self.selected_day = None
        self.refresh_ui()

    def _next_month(self, e=None):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self.selected_day = None
        self.refresh_ui()

    def _go_to_today(self, e=None):
        now = datetime.now()
        self.current_year = now.year
        self.current_month = now.month
        self.selected_day = None
        self.refresh_ui()

    def _on_day_selected(self, day: int | None):
        self.selected_day = day
        self.refresh_ui()

    def _on_search_change(self, e):
        self.search_query = (e.control.value or "").strip().lower()
        self.refresh_ui()

    def _set_history_filter(self, filter_type: str):
        self.history_filter_type = filter_type
        self.refresh_ui()

    # --- Sincronización Asíncrona en Segundo Plano ---
    def _background_sync(self, notify_user: bool = False):
        online, count, status_msg = self.supabase_service.sync_pending_transactions()
        self.refresh_ui()
        if notify_user:
            self.page.open(ft.SnackBar(content=ft.Text(status_msg), duration=2500))

    def _on_auth_changed(self, msg: str, sync: bool = True):
        self.refresh_ui()
        self.page.open(ft.SnackBar(content=ft.Text(msg), duration=2500))
        if sync and self.supabase_service.user_id:
            self.page.run_thread(self._background_sync, True)

    def handle_save_transaction(
        self,
        tx_id: str | None,
        tx_type: str,
        amount: float,
        category: str,
        note: str,
        created_at: str | None = None,
    ):
        uid = self.supabase_service.user_id or "local_user"
        if tx_id is None:
            self.local_storage.add_transaction_local(
                tx_type, amount, category, note, user_id=uid, created_at=created_at
            )
            msg = "Movimiento registrado"
        else:
            self.local_storage.update_transaction_local(
                tx_id, tx_type, amount, category, note, created_at=created_at
            )
            msg = "Movimiento actualizado"

        # Si el usuario registró en otro mes/año, saltamos a ese mes para que lo vea de inmediato
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at[:19])
                self.current_year = dt.year
                self.current_month = dt.month
            except Exception:
                pass

        self.refresh_ui()
        self.page.open(ft.SnackBar(content=ft.Text(msg), duration=1800))
        self.page.run_thread(self._background_sync, False)

    def trigger_manual_sync(self, e):
        if not self.supabase_service.user_id:
            self.auth_modal.open()
            return
        self.page.open(ft.SnackBar(content=ft.Text("Sincronizando con Supabase..."), duration=1200))
        self.page.run_thread(self._background_sync, True)

    def export_csv_to_clipboard(self, transactions: list[dict]):
        if not transactions:
            self.page.open(ft.SnackBar(content=ft.Text("No hay movimientos para exportar."), duration=2000))
            return
        lines = ["Fecha,Tipo,Categoria,Metodo,Nota,Monto"]
        for t in transactions:
            method, clean_note = parse_payment_and_note(t.get("note", ""))
            safe_note = clean_note.replace('"', '""')
            lines.append(
                f'{str(t.get("created_at", ""))[:10]},{t["type"]},"{t["category"]}","{method}","{safe_note}",{t["amount"]:.2f}'
            )
        csv_text = "\n".join(lines)
        self.page.set_clipboard(csv_text)
        self.page.open(
            ft.SnackBar(
                content=ft.Text(f"CSV copiado al portapapeles ({len(transactions)} movimientos). Pégalo en Excel o WhatsApp."),
                duration=3000,
            )
        )

    # --- Flujo de Confirmación Antes de Borrar ---
    def ask_delete_confirmation(self, tx: dict):
        self.tx_to_delete = tx
        tipo_label = "gasto" if tx["type"] == "gasto" else "ingreso"
        _, clean_note = parse_payment_and_note(tx.get("note", ""))
        nota_info = f" ({clean_note})" if clean_note else ""
        self.delete_warning_text.value = (
            f"¿Deseas borrar este {tipo_label} de {tx['category']}{nota_info} "
            f"por {CURRENCY_SYMBOL} {tx['amount']:,.2f}?\n\nEsta acción no se puede deshacer."
        )
        self.page.open(self.confirm_delete_dialog)

    def _confirm_delete_execution(self, e):
        self.page.close(self.confirm_delete_dialog)
        if not self.tx_to_delete:
            return

        tx_id = self.tx_to_delete["id"]
        self.tx_to_delete = None

        self.local_storage.delete_transaction_local(tx_id)
        self.refresh_ui()
        self.page.open(ft.SnackBar(content=ft.Text("Movimiento eliminado"), duration=1800))
        self.page.run_thread(self._background_sync, False)

    # --- Retorno de Deep Link OAuth ---
    def handle_auth_callback(self, auth_code: str):
        if getattr(self, "_last_auth_code", None) == auth_code:
            return
        self._last_auth_code = auth_code

        def _worker():
            ok, msg = self.supabase_service.complete_login_with_code(auth_code)
            self.refresh_ui()
            self.page.open(ft.SnackBar(content=ft.Text(msg), duration=2500))
            if ok:
                self._background_sync(True)

        self.page.run_thread(_worker)

    def toggle_theme(self, e):
        self.page.theme_mode = (
            ft.ThemeMode.LIGHT if self.page.theme_mode == ft.ThemeMode.DARK else ft.ThemeMode.DARK
        )
        self.page.update()

    # --- Construcción de Tarjetas de Movimiento sin Desbordes ---
    def _build_tx_card(self, tx: dict, all_categories: dict) -> ft.Container:
        is_expense = tx["type"] == "gasto"
        cat_meta = all_categories.get(tx["category"], {"icon": ft.Icons.RECEIPT, "color": "grey"})
        sign = "-" if is_expense else "+"
        amount_color = "red400" if is_expense else "teal400"
        sync_icon = ft.Icons.CLOUD_DONE if tx.get("synced") else ft.Icons.CLOUD_OFF

        payment_method, clean_note = parse_payment_and_note(tx.get("note", ""))
        date_str = str(tx.get("created_at", ""))[:10]
        subtitle_str = clean_note if clean_note else f"{payment_method} • {date_str}"

        return ft.Container(
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border_radius=14,
            bgcolor="surfaceVariant",
            content=ft.Column(
                spacing=6,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Row(
                                spacing=10,
                                expand=True,
                                controls=[
                                    ft.Container(
                                        padding=8,
                                        border_radius=10,
                                        bgcolor="background",
                                        content=ft.Icon(cat_meta["icon"], color=cat_meta["color"], size=18),
                                    ),
                                    ft.Column(
                                        spacing=2,
                                        expand=True,
                                        controls=[
                                            ft.Text(
                                                tx["category"],
                                                weight=ft.FontWeight.BOLD,
                                                size=13,
                                                no_wrap=True,
                                                overflow=ft.TextOverflow.ELLIPSIS,
                                            ),
                                            ft.Text(
                                                subtitle_str,
                                                size=11,
                                                color="onSurfaceVariant",
                                                no_wrap=True,
                                                overflow=ft.TextOverflow.ELLIPSIS,
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            ft.Text(
                                f"{sign} {CURRENCY_SYMBOL} {tx['amount']:,.2f}",
                                weight=ft.FontWeight.BOLD,
                                size=14,
                                color=amount_color,
                                no_wrap=True,
                            ),
                        ],
                    ),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Row(
                                spacing=5,
                                expand=True,
                                controls=[
                                    ft.Icon(
                                        sync_icon,
                                        size=13,
                                        color="teal400" if tx.get("synced") else "onSurfaceVariant",
                                    ),
                                    ft.Text(
                                        f"{date_str} • {payment_method}",
                                        size=11,
                                        color="onSurfaceVariant",
                                        no_wrap=True,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                ],
                            ),
                            ft.Row(
                                spacing=0,
                                tight=True,
                                controls=[
                                    ft.IconButton(
                                        icon=ft.Icons.EDIT_OUTLINED,
                                        icon_size=17,
                                        tooltip="Editar movimiento",
                                        style=ft.ButtonStyle(padding=6),
                                        on_click=lambda e, item=tx: self.modal.open_for_edit(item),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        icon_size=17,
                                        icon_color="red400",
                                        tooltip="Eliminar movimiento",
                                        style=ft.ButtonStyle(padding=6),
                                        on_click=lambda e, item=tx: self.ask_delete_confirmation(item),
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        )

    def _build_month_selector_bar(self, month_label: str) -> ft.Container:
        now = datetime.now()
        is_current = self.current_year == now.year and self.current_month == now.month
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
            border_radius=12,
            bgcolor="surfaceVariant",
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.CHEVRON_LEFT,
                        icon_size=20,
                        tooltip="Mes anterior",
                        style=ft.ButtonStyle(padding=4),
                        on_click=self._prev_month,
                    ),
                    ft.Row(
                        spacing=6,
                        tight=True,
                        controls=[
                            ft.Icon(ft.Icons.CALENDAR_TODAY, size=15, color="teal400"),
                            ft.Text(
                                f"{MONTH_FULL_NAMES[self.current_month]} {self.current_year}",
                                weight=ft.FontWeight.BOLD,
                                size=14,
                            ),
                            ft.TextButton(
                                "Ir a Hoy",
                                style=ft.ButtonStyle(padding=ft.padding.symmetric(horizontal=6, vertical=2)),
                                on_click=self._go_to_today,
                            )
                            if not is_current
                            else ft.Container(),
                        ],
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CHEVRON_RIGHT,
                        icon_size=20,
                        tooltip="Mes siguiente",
                        style=ft.ButtonStyle(padding=4),
                        on_click=self._next_month,
                    ),
                ],
            ),
        )

    def _build_grouped_history(self, filtered_txs: list[dict], all_categories: dict) -> list[ft.Control]:
        if not filtered_txs:
            return [
                ft.Container(
                    padding=24,
                    border_radius=14,
                    bgcolor="surfaceVariant",
                    alignment=ft.alignment.center,
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=6,
                        controls=[
                            ft.Icon(ft.Icons.HISTORY_TOGGLE_OFF, size=34, color="onSurfaceVariant"),
                            ft.Text(
                                "No hay movimientos en esta fecha o filtro.",
                                size=13,
                                color="onSurfaceVariant",
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                    ),
                )
            ]

        by_date: dict[str, list[dict]] = {}
        for tx in filtered_txs:
            d_key = str(tx.get("created_at", ""))[:10]
            by_date.setdefault(d_key, []).append(tx)

        groups: list[ft.Control] = []
        for d_key in sorted(by_date.keys(), reverse=True):
            day_items = by_date[d_key]
            day_inc = sum(t["amount"] for t in day_items if t["type"] == "ingreso")
            day_exp = sum(t["amount"] for t in day_items if t["type"] == "gasto")
            day_net = day_inc - day_exp
            net_sign = "+" if day_net >= 0 else ""

            try:
                dt = datetime.strptime(d_key, "%Y-%m-%d")
                w_name = WEEKDAYS_ES[dt.weekday()]
                nice_date = f"{w_name}, {dt.day:02d} {MONTH_NAMES[dt.month]} {dt.year}"
            except Exception:
                nice_date = d_key

            groups.append(
                ft.Container(
                    padding=ft.padding.only(top=6, bottom=2, left=4, right=4),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(nice_date, size=12, weight=ft.FontWeight.BOLD, color="onSurfaceVariant"),
                            ft.Text(
                                f"Neto día: {net_sign}{CURRENCY_SYMBOL} {day_net:,.2f}",
                                size=12,
                                weight=ft.FontWeight.W_600,
                                color="teal400" if day_net >= 0 else "red400",
                            ),
                        ],
                    ),
                )
            )
            for item in day_items:
                groups.append(self._build_tx_card(item, all_categories))

        return groups

    def refresh_ui(self):
        if self.supabase_service.user_email:
            short_name = self.supabase_service.user_email.split("@")[0][:10]
            self.auth_button.text = short_name
            self.auth_button.icon = ft.Icons.VERIFIED_USER
        else:
            self.auth_button.text = "Cuenta"
            self.auth_button.icon = ft.Icons.ACCOUNT_CIRCLE

        transactions = self.local_storage.get_transactions()
        pending_count = len(self.local_storage.get_pending_queue()) + len(self.local_storage.get_pending_deletes())

        target_ym = f"{self.current_year:04d}-{self.current_month:02d}"
        month_label = f"{MONTH_NAMES[self.current_month]} {self.current_year}"

        # Saldo histórico total
        all_income = sum(t["amount"] for t in transactions if t["type"] == "ingreso")
        all_expense = sum(t["amount"] for t in transactions if t["type"] == "gasto")
        all_time_balance = all_income - all_expense

        # Movimientos del mes seleccionado
        monthly_transactions = [
            t for t in transactions if str(t.get("created_at", "")).startswith(target_ym)
        ]
        monthly_income = sum(t["amount"] for t in monthly_transactions if t["type"] == "ingreso")
        monthly_expense = sum(t["amount"] for t in monthly_transactions if t["type"] == "gasto")

        all_categories = {**EXPENSE_CATEGORIES, **INCOME_CATEGORIES}

        if self.active_tab == 0:
            # --- PESTAÑA 0: RESUMEN (DASHBOARD) ---
            recent_cards = [self._build_tx_card(tx, all_categories) for tx in monthly_transactions[:8]]
            self.main_column.controls = [
                self._build_month_selector_bar(month_label),
                build_summary_cards(
                    all_time_balance,
                    monthly_income,
                    monthly_expense,
                    pending_count,
                    month_label,
                ),
                build_budget_50_30_20_card(monthly_transactions, monthly_income),
                ft.ResponsiveRow(
                    spacing=12,
                    run_spacing=12,
                    controls=[
                        ft.Container(
                            col={"xs": 12, "sm": 12, "md": 7},
                            content=build_expense_pie_chart(monthly_transactions),
                        ),
                        ft.Container(
                            col={"xs": 12, "sm": 12, "md": 5},
                            content=build_cashflow_bar_chart(monthly_income, monthly_expense),
                        ),
                    ],
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text(f"Movimientos de {month_label}", size=15, weight=ft.FontWeight.BOLD),
                        ft.TextButton(
                            "Ver Calendario →",
                            on_click=lambda e: self.switch_to_tab(1),
                        ),
                    ],
                ),
                ft.Column(
                    spacing=8,
                    controls=recent_cards
                    if recent_cards
                    else [
                        ft.Container(
                            padding=18,
                            border_radius=12,
                            bgcolor="surfaceVariant",
                            alignment=ft.alignment.center,
                            content=ft.Text(
                                f"Sin movimientos en {month_label}. Usa los botones inferiores para registrar.",
                                size=12,
                                color="onSurfaceVariant",
                                text_align=ft.TextAlign.CENTER,
                            ),
                        )
                    ],
                ),
                ft.Container(height=8),
            ]
        else:
            # --- PESTAÑA 1: CALENDARIO E HISTORIAL ---
            calendar_widget = build_interactive_calendar(
                year=self.current_year,
                month=self.current_month,
                selected_day=self.selected_day,
                month_transactions=monthly_transactions,
                on_day_click=self._on_day_selected,
                on_prev_month=self._prev_month,
                on_next_month=self._next_month,
                on_add_for_date=lambda dt: self.modal.open_for_create("gasto", initial_date=dt),
            )

            # Filtrar por día (si hay uno seleccionado en el calendario), tipo y búsqueda
            filtered = monthly_transactions
            if self.selected_day is not None:
                target_ymd = f"{self.current_year:04d}-{self.current_month:02d}-{self.selected_day:02d}"
                filtered = [t for t in filtered if str(t.get("created_at", "")).startswith(target_ymd)]

            if self.history_filter_type in ("gasto", "ingreso"):
                filtered = [t for t in filtered if t["type"] == self.history_filter_type]

            if self.search_query:
                filtered = [
                    t
                    for t in filtered
                    if self.search_query in str(t.get("category", "")).lower()
                    or self.search_query in str(t.get("note", "")).lower()
                ]

            filter_row = ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                wrap=True,
                spacing=6,
                controls=[
                    ft.Row(
                        spacing=6,
                        tight=True,
                        controls=[
                            ft.Chip(
                                label=ft.Text("Todos", size=11),
                                selected=(self.history_filter_type == "todos"),
                                on_select=lambda e: self._set_history_filter("todos"),
                            ),
                            ft.Chip(
                                label=ft.Text("Gastos", size=11),
                                selected=(self.history_filter_type == "gasto"),
                                on_select=lambda e: self._set_history_filter("gasto"),
                            ),
                            ft.Chip(
                                label=ft.Text("Ingresos", size=11),
                                selected=(self.history_filter_type == "ingreso"),
                                on_select=lambda e: self._set_history_filter("ingreso"),
                            ),
                        ],
                    ),
                    ft.TextButton(
                        "Exportar CSV",
                        icon=ft.Icons.DOWNLOAD_OUTLINED,
                        style=ft.ButtonStyle(padding=ft.padding.symmetric(horizontal=8, vertical=4)),
                        on_click=lambda e, items=filtered: self.export_csv_to_clipboard(items),
                    ),
                ],
            )

            self.main_column.controls = [
                calendar_widget,
                self.search_input,
                filter_row,
                ft.Column(
                    spacing=8,
                    controls=self._build_grouped_history(filtered, all_categories),
                ),
                ft.Container(height=8),
            ]

        self.page.update()

    def build(self):
        self.page.floating_action_button = None

        self.page.appbar = ft.AppBar(
            title=ft.Text(
                "Mis Finanzas (S/)",
                size=17,
                weight=ft.FontWeight.BOLD,
                no_wrap=True,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
            center_title=False,
            actions=[
                ft.IconButton(
                    ft.Icons.SYNC,
                    icon_size=20,
                    tooltip="Sincronizar con la nube",
                    on_click=self.trigger_manual_sync,
                ),
                ft.IconButton(
                    ft.Icons.DARK_MODE_OUTLINED,
                    icon_size=20,
                    tooltip="Cambiar tema",
                    on_click=self.toggle_theme,
                ),
                self.auth_button,
                ft.Container(width=6),
            ],
        )

        def _default_date_for_create() -> datetime | None:
            if self.selected_day is not None:
                try:
                    return datetime(self.current_year, self.current_month, self.selected_day)
                except Exception:
                    return None
            return None

        bottom_action_bar = ft.Container(
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            bgcolor="surfaceVariant",
            border=ft.border.only(top=ft.BorderSide(1, "outlineVariant")),
            content=ft.Row(
                spacing=10,
                controls=[
                    ft.FilledButton(
                        text="- Gasto",
                        icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,
                        bgcolor="red400",
                        color="white",
                        expand=True,
                        height=42,
                        on_click=lambda e: self.modal.open_for_create("gasto", _default_date_for_create()),
                    ),
                    ft.FilledButton(
                        text="+ Ingreso",
                        icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                        bgcolor="teal400",
                        color="white",
                        expand=True,
                        height=42,
                        on_click=lambda e: self.modal.open_for_create("ingreso", _default_date_for_create()),
                    ),
                ],
            ),
        )

        self.refresh_ui()

        if self.supabase_service.user_id:
            self.page.run_thread(self._background_sync, False)

        return ft.Column(
            spacing=0,
            expand=True,
            controls=[
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=14, vertical=8),
                    expand=True,
                    content=self.main_column,
                ),
                bottom_action_bar,
                self.nav_bar,
            ],
        )