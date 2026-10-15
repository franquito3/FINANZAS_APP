from datetime import datetime
import flet as ft
from config.settings import CURRENCY_SYMBOL, EXPENSE_CATEGORIES, INCOME_CATEGORIES
from ui.components.summary_cards import build_summary_cards
from ui.components.charts import build_expense_pie_chart, build_cashflow_bar_chart
from ui.components.quick_modal import TransactionModal

MONTH_NAMES = {
    1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"
}

class DashboardView:
    def __init__(self, page: ft.Page, local_storage, supabase_service):
        self.page = page
        self.local_storage = local_storage
        self.supabase_service = supabase_service
        self.main_column = ft.Column(spacing=16, scroll=ft.ScrollMode.HIDDEN, expand=True)
        self.modal = TransactionModal(self.page, self.handle_save_transaction)
        self.auth_button = ft.FilledTonalButton("Google", icon=ft.Icons.ACCOUNT_CIRCLE, on_click=self.on_auth_button_click)

        # Estado y diálogo de confirmación antes de borrar
        self.tx_to_delete: dict | None = None
        self.delete_warning_text = ft.Text("")
        self.confirm_delete_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color="red400"),
                    ft.Text("Confirmar eliminación", weight=ft.FontWeight.BOLD, size=18),
                ],
            ),
            content=self.delete_warning_text,
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.page.close(self.confirm_delete_dialog)),
                ft.FilledButton(
                    "Sí, eliminar",
                    icon=ft.Icons.DELETE_FOREVER,
                    bgcolor="red400",
                    color="white",
                    on_click=self._confirm_delete_execution,
                ),
            ],
        )

        # Diálogo para cerrar sesión de Google
        self.logout_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Cuenta Conectada", weight=ft.FontWeight.BOLD),
            content=ft.Text("¿Deseas cerrar tu sesión de Google en este dispositivo? Tus datos locales se mantendrán intactos."),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.page.close(self.logout_dialog)),
                ft.FilledButton("Cerrar Sesión", bgcolor="red400", color="white", on_click=self._confirm_logout),
            ],
        )

    # --- Sincronización Asíncrona en Segundo Plano ---
    def _background_sync(self, notify_user: bool = False):
        online, count, status_msg = self.supabase_service.sync_pending_transactions()
        self.refresh_ui()
        if notify_user:
            self.page.open(ft.SnackBar(content=ft.Text(status_msg), duration=2500))

    def handle_save_transaction(self, tx_id: str | None, tx_type: str, amount: float, category: str, note: str):
        uid = self.supabase_service.user_id or "local_user"
        if tx_id is None:
            self.local_storage.add_transaction_local(tx_type, amount, category, note, user_id=uid)
            msg = "Movimiento registrado"
        else:
            self.local_storage.update_transaction_local(tx_id, tx_type, amount, category, note)
            msg = "Movimiento actualizado"

        # 1. Actualización visual instantánea (<10ms)
        self.refresh_ui()
        self.page.open(ft.SnackBar(content=ft.Text(msg), duration=1800))

        # 2. Subida a Supabase en hilo secundario sin congelar la UI
        self.page.run_thread(self._background_sync, False)

    def trigger_manual_sync(self, e):
        self.page.open(ft.SnackBar(content=ft.Text("Sincronizando con Supabase..."), duration=1200))
        self.page.run_thread(self._background_sync, True)

    # --- Flujo de Confirmación Antes de Borrar ---
    def ask_delete_confirmation(self, tx: dict):
        self.tx_to_delete = tx
        tipo_label = "gasto" if tx["type"] == "gasto" else "ingreso"
        nota_info = f" ({tx['note']})" if tx.get("note") else ""
        self.delete_warning_text.value = (
            f"¿Estás seguro de que deseas borrar este {tipo_label} de "
            f"{tx['category']}{nota_info} por {CURRENCY_SYMBOL} {tx['amount']:,.2f}?\n\n"
            f"Esta acción no se puede deshacer."
        )
        self.page.open(self.confirm_delete_dialog)

    def _confirm_delete_execution(self, e):
        self.page.close(self.confirm_delete_dialog)
        if not self.tx_to_delete:
            return

        tx_id = self.tx_to_delete["id"]
        self.tx_to_delete = None

        # 1. Borrado inmediato en caché local y encolado en lista negra anti-zombie
        self.local_storage.delete_transaction_local(tx_id)
        self.refresh_ui()
        self.page.open(ft.SnackBar(content=ft.Text("Movimiento eliminado"), duration=1800))

        # 2. Ejecución del DELETE remoto en segundo plano
        self.page.run_thread(self._background_sync, False)

    # --- Autenticación y Sesión ---
    def _on_google_auth_complete(self):
        self.page.run_thread(self._background_sync, True)

    def on_auth_button_click(self, e):
        if self.supabase_service.user_email:
            self.page.open(self.logout_dialog)
            return

        url = self.supabase_service.start_google_login(self._on_google_auth_complete)
        if url:
            self.page.launch_url(url)
        else:
            self.page.open(
                ft.SnackBar(
                    content=ft.Text("Configura tus claves SUPABASE_URL y SUPABASE_KEY en settings.py o .env"),
                    bgcolor="amber",
                )
            )

    def _confirm_logout(self, e):
        self.page.close(self.logout_dialog)
        self.supabase_service.logout()
        self.refresh_ui()
        self.page.open(ft.SnackBar(content=ft.Text("Sesión cerrada correctamente"), duration=2000))

    def toggle_theme(self, e):
        self.page.theme_mode = (
            ft.ThemeMode.LIGHT if self.page.theme_mode == ft.ThemeMode.DARK else ft.ThemeMode.DARK
        )
        self.page.update()

    def refresh_ui(self):
        if self.supabase_service.user_email:
            short_name = self.supabase_service.user_email.split("@")[0]
            self.auth_button.text = short_name
            self.auth_button.icon = ft.Icons.VERIFIED_USER
        else:
            self.auth_button.text = "Google"
            self.auth_button.icon = ft.Icons.ACCOUNT_CIRCLE

        transactions = self.local_storage.get_transactions()
        pending_count = len(self.local_storage.get_pending_queue()) + len(self.local_storage.get_pending_deletes())

        now = datetime.now()
        current_YearMonth = now.strftime("%Y-%m")
        month_label = f"{MONTH_NAMES[now.month]} {now.year}"

        # Saldo histórico total (todos los ingresos menos todos los gastos)
        all_income = sum(t["amount"] for t in transactions if t["type"] == "ingreso")
        all_expense = sum(t["amount"] for t in transactions if t["type"] == "gasto")
        all_time_balance = all_income - all_expense

        # Movimientos exclusivos del mes actual para tarjetas mensuales y gráficos
        monthly_transactions = [
            t for t in transactions if str(t.get("created_at", "")).startswith(current_YearMonth)
        ]
        monthly_income = sum(t["amount"] for t in monthly_transactions if t["type"] == "ingreso")
        monthly_expense = sum(t["amount"] for t in monthly_transactions if t["type"] == "gasto")

        all_categories = {**EXPENSE_CATEGORIES, **INCOME_CATEGORIES}

        tx_items = []
        for tx in transactions[:25]:
            is_expense = tx["type"] == "gasto"
            cat_meta = all_categories.get(tx["category"], {"icon": ft.Icons.RECEIPT, "color": "grey"})
            sign = "-" if is_expense else "+"
            amount_color = "red400" if is_expense else "teal400"
            sync_icon = ft.Icons.CLOUD_DONE if tx.get("synced") else ft.Icons.CLOUD_OFF

            tx_items.append(
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=14, vertical=12),
                    border_radius=14,
                    bgcolor="surfaceVariant",
                    content=ft.Column(
                        spacing=8,
                        controls=[
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.Row(
                                        spacing=12,
                                        expand=True,
                                        controls=[
                                            ft.Container(
                                                padding=10,
                                                border_radius=10,
                                                bgcolor="background",
                                                content=ft.Icon(cat_meta["icon"], color=cat_meta["color"], size=20),
                                            ),
                                            ft.Column(
                                                spacing=2,
                                                expand=True,
                                                controls=[
                                                    ft.Text(
                                                        tx["category"],
                                                        weight=ft.FontWeight.BOLD,
                                                        size=14,
                                                        no_wrap=True,
                                                        overflow=ft.TextOverflow.ELLIPSIS,
                                                    ),
                                                    ft.Text(
                                                        tx["note"] or tx["created_at"][:10],
                                                        size=12,
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
                                        size=15,
                                        color=amount_color,
                                    ),
                                ],
                            ),
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.Row(
                                        spacing=6,
                                        controls=[
                                            ft.Icon(sync_icon, size=14, color="teal400" if tx.get("synced") else "onSurfaceVariant"),
                                            ft.Text(
                                                f"{tx['created_at'][:10]} • " + ("En la nube" if tx.get("synced") else "En dispositivo"),
                                                size=11,
                                                color="onSurfaceVariant",
                                            ),
                                        ],
                                    ),
                                    ft.Row(
                                        spacing=0,
                                        controls=[
                                            ft.TextButton(
                                                text="Editar",
                                                icon=ft.Icons.EDIT_OUTLINED,
                                                style=ft.ButtonStyle(padding=ft.padding.symmetric(horizontal=8, vertical=4)),
                                                on_click=lambda e, item=tx: self.modal.open_for_edit(item),
                                            ),
                                            ft.TextButton(
                                                text="Borrar",
                                                icon=ft.Icons.DELETE_OUTLINE,
                                                icon_color="red400",
                                                style=ft.ButtonStyle(
                                                    color="red400",
                                                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                                                ),
                                                on_click=lambda e, item=tx: self.ask_delete_confirmation(item),
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                )
            )

        self.main_column.controls = [
            build_summary_cards(all_time_balance, monthly_income, monthly_expense, pending_count, month_label),
            ft.ResponsiveRow(
                spacing=12,
                run_spacing=12,
                controls=[
                    ft.Container(col={"sm": 12, "md": 7}, content=build_expense_pie_chart(monthly_transactions)),
                    ft.Container(col={"sm": 12, "md": 5}, content=build_cashflow_bar_chart(monthly_income, monthly_expense)),
                ],
            ),
            ft.Text("Movimientos Recientes", size=17, weight=ft.FontWeight.BOLD),
            ft.Column(
                spacing=10,
                controls=tx_items if tx_items else [
                    ft.Container(
                        padding=20,
                        border_radius=12,
                        bgcolor="surfaceVariant",
                        alignment=ft.alignment.center,
                        content=ft.Text("Usa los botones inferiores para registrar tu primer ingreso o gasto.", color="onSurfaceVariant"),
                    )
                ],
            ),
            ft.Container(height=12),
        ]
        self.page.update()

    def build(self):
        self.page.floating_action_button = None

        self.page.appbar = ft.AppBar(
            title=ft.Text("Mis Finanzas (S/)", weight=ft.FontWeight.BOLD),
            center_title=False,
            actions=[
                ft.IconButton(ft.Icons.SYNC, tooltip="Sincronizar con la nube", on_click=self.trigger_manual_sync),
                ft.IconButton(ft.Icons.DARK_MODE_OUTLINED, tooltip="Cambiar tema", on_click=self.toggle_theme),
                self.auth_button,
                ft.Container(width=8),
            ],
        )

        bottom_action_bar = ft.Container(
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            bgcolor="surfaceVariant",
            border=ft.border.only(top=ft.BorderSide(1, "outlineVariant")),
            content=ft.Row(
                spacing=12,
                controls=[
                    ft.FilledButton(
                        text="Registrar Gasto",
                        icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,
                        bgcolor="red400",
                        color="white",
                        expand=True,
                        height=46,
                        on_click=lambda e: self.modal.open_for_create("gasto"),
                    ),
                    ft.FilledButton(
                        text="Registrar Ingreso",
                        icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                        bgcolor="teal400",
                        color="white",
                        expand=True,
                        height=46,
                        on_click=lambda e: self.modal.open_for_create("ingreso"),
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
                ft.Container(padding=ft.padding.symmetric(horizontal=16, vertical=10), expand=True, content=self.main_column),
                bottom_action_bar,
            ],
        )