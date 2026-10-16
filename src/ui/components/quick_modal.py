from datetime import datetime, timedelta
import flet as ft
from config.settings import (
    CURRENCY_SYMBOL,
    EXPENSE_CATEGORIES,
    INCOME_CATEGORIES,
    MAX_TRANSACTION_AMOUNT,
    PAYMENT_METHODS,
)


def parse_payment_and_note(raw_note: str | None) -> tuple[str, str]:
    """Extrae el método de pago si está codificado al inicio de la nota '[Método] Nota'."""
    text = (raw_note or "").strip()
    if text.startswith("[") and "]" in text:
        end_idx = text.find("]")
        maybe_method = text[1:end_idx].strip()
        if maybe_method in PAYMENT_METHODS:
            return maybe_method, text[end_idx + 1 :].strip()
    return PAYMENT_METHODS[0], text


def format_payment_and_note(payment_method: str, clean_note: str) -> str:
    note = (clean_note or "").strip()
    method = (payment_method or PAYMENT_METHODS[0]).strip()
    prefix = f"[{method}]"
    if note:
        return f"{prefix} {note}"[:90]
    return prefix


class TransactionModal:
    def __init__(self, page: ft.Page, on_save_callback):
        self.page = page
        self.on_save_callback = on_save_callback
        self.editing_tx_id: str | None = None
        self.selected_type = "gasto"
        self.selected_category = list(EXPENSE_CATEGORIES.keys())[0]
        self.selected_payment = PAYMENT_METHODS[0]
        self.selected_date: datetime = datetime.now()

        self.title_text = ft.Text("Registrar Movimiento", weight=ft.FontWeight.BOLD, size=18)

        # Sin autofocus=True para evitar que el teclado oculte las categorías al abrir en móvil
        self.amount_input = ft.TextField(
            label=f"Monto ({CURRENCY_SYMBOL})",
            prefix_text=f"{CURRENCY_SYMBOL} ",
            keyboard_type=ft.KeyboardType.NUMBER,
            autofocus=False,
            text_size=18,
            border_radius=12,
            content_padding=ft.padding.symmetric(horizontal=14, vertical=12),
            on_submit=self._save,
        )

        self.note_input = ft.TextField(
            label="Nota o detalle (opcional)",
            max_length=70,
            border_radius=12,
            text_size=14,
            content_padding=ft.padding.symmetric(horizontal=14, vertical=10),
            on_submit=self._save,
        )

        # Selector de Fecha con DatePicker nativo
        self.date_label = ft.Text("", size=13, weight=ft.FontWeight.W_600)
        self.date_picker = ft.DatePicker(
            first_date=datetime(2020, 1, 1),
            last_date=datetime(2035, 12, 31),
            on_change=self._on_date_picked,
            help_text="Selecciona la fecha del movimiento",
            cancel_text="Cancelar",
            confirm_text="Aceptar",
        )

        self.category_chips_container = ft.Row(wrap=True, spacing=6, run_spacing=6)
        self.payment_chips_container = ft.Row(wrap=True, spacing=6, run_spacing=6)

        self.type_selector = ft.SegmentedButton(
            selected={"gasto"},
            allow_multiple_selection=False,
            on_change=self._on_type_change,
            segments=[
                ft.Segment(
                    value="gasto",
                    label=ft.Text("Gasto", size=13),
                    icon=ft.Icon(ft.Icons.REMOVE_CIRCLE_OUTLINE, size=18),
                ),
                ft.Segment(
                    value="ingreso",
                    label=ft.Text("Ingreso", size=13),
                    icon=ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE, size=18),
                ),
            ],
        )

        # Contenedor con scroll interno y altura controlada para evitar cualquier desborde con el teclado
        self.scrollable_body = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            tight=True,
            spacing=10,
            controls=[
                ft.Container(alignment=ft.alignment.center, content=self.type_selector),
                self.amount_input,
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=10, vertical=8),
                    border_radius=10,
                    bgcolor="surfaceVariant",
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        wrap=True,
                        spacing=6,
                        controls=[
                            ft.Row(
                                spacing=6,
                                tight=True,
                                controls=[
                                    ft.Icon(ft.Icons.CALENDAR_MONTH, size=18, color="teal400"),
                                    self.date_label,
                                ],
                            ),
                            ft.Row(
                                spacing=4,
                                tight=True,
                                controls=[
                                    ft.TextButton(
                                        "Hoy",
                                        style=ft.ButtonStyle(padding=ft.padding.symmetric(horizontal=8, vertical=2)),
                                        on_click=lambda e: self._set_quick_date(0),
                                    ),
                                    ft.TextButton(
                                        "Ayer",
                                        style=ft.ButtonStyle(padding=ft.padding.symmetric(horizontal=8, vertical=2)),
                                        on_click=lambda e: self._set_quick_date(-1),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.EDIT_CALENDAR,
                                        icon_size=18,
                                        tooltip="Elegir otra fecha",
                                        style=ft.ButtonStyle(padding=4),
                                        on_click=self._open_date_picker,
                                    ),
                                ],
                            ),
                        ],
                    ),
                ),
                ft.Text("Categoría:", size=12, weight=ft.FontWeight.W_600, color="onSurfaceVariant"),
                self.category_chips_container,
                ft.Text("Método / Cuenta:", size=12, weight=ft.FontWeight.W_600, color="onSurfaceVariant"),
                self.payment_chips_container,
                self.note_input,
            ],
        )

        self.dialog_container = ft.Container(
            width=330,
            height=350,
            content=self.scrollable_body,
        )

        self.dialog = ft.AlertDialog(
            modal=True,
            inset_padding=ft.padding.symmetric(horizontal=14, vertical=16),
            title_padding=ft.padding.only(left=18, top=16, right=18, bottom=6),
            content_padding=ft.padding.only(left=18, top=8, right=18, bottom=8),
            actions_padding=ft.padding.only(left=12, top=4, right=16, bottom=12),
            title=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    self.title_text,
                    ft.IconButton(
                        icon=ft.Icons.CLOSE,
                        icon_size=20,
                        tooltip="Cerrar",
                        on_click=lambda e: self.page.close(self.dialog),
                    ),
                ],
            ),
            content=self.dialog_container,
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.page.close(self.dialog)),
                ft.FilledButton("Guardar", icon=ft.Icons.CHECK, on_click=self._save),
            ],
        )

    def _adjust_modal_size(self):
        """Ajusta dinámicamente el alto del cuerpo del modal según la pantalla para evitar desbordes."""
        page_h = self.page.height or 760
        page_w = self.page.width or 380
        self.dialog_container.width = min(max(page_w - 56, 260), 400)
        self.dialog_container.height = min(max(int(page_h * 0.52), 260), 420)

    def _update_date_label(self):
        today = datetime.now().date()
        target = self.selected_date.date()
        diff = (today - target).days
        suffix = " (Hoy)" if diff == 0 else (" (Ayer)" if diff == 1 else "")
        self.date_label.value = f"{self.selected_date.strftime('%d/%m/%Y')}{suffix}"

    def _set_quick_date(self, offset_days: int):
        now = datetime.now()
        self.selected_date = now + timedelta(days=offset_days)
        self._update_date_label()
        self.page.update()

    def _open_date_picker(self, e):
        self.date_picker.value = self.selected_date
        self.page.open(self.date_picker)

    def _on_date_picked(self, e):
        if self.date_picker.value:
            picked = self.date_picker.value
            now = datetime.now()
            self.selected_date = datetime(
                picked.year,
                picked.month,
                picked.day,
                now.hour,
                now.minute,
                now.second,
            )
            self._update_date_label()
            self.page.update()

    def _render_category_chips(self):
        categories = EXPENSE_CATEGORIES if self.selected_type == "gasto" else INCOME_CATEGORIES
        if self.selected_category not in categories:
            self.selected_category = list(categories.keys())[0]

        self.category_chips_container.controls.clear()
        for cat_name, meta in categories.items():
            is_sel = self.selected_category == cat_name
            self.category_chips_container.controls.append(
                ft.Chip(
                    label=ft.Text(cat_name, size=11, weight=ft.FontWeight.W_600 if is_sel else ft.FontWeight.NORMAL),
                    leading=ft.Icon(meta["icon"], size=15, color=meta["color"]),
                    selected=is_sel,
                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    on_select=lambda e, c=cat_name: self._select_cat(c),
                )
            )

        self.payment_chips_container.controls.clear()
        for method in PAYMENT_METHODS:
            is_pm = self.selected_payment == method
            self.payment_chips_container.controls.append(
                ft.Chip(
                    label=ft.Text(method, size=11, weight=ft.FontWeight.W_600 if is_pm else ft.FontWeight.NORMAL),
                    selected=is_pm,
                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    on_select=lambda e, m=method: self._select_payment(m),
                )
            )
        self.page.update()

    def _select_cat(self, cat_name: str):
        self.selected_category = cat_name
        self._render_category_chips()

    def _select_payment(self, method: str):
        self.selected_payment = method
        self._render_category_chips()

    def _on_type_change(self, e):
        if e.control.selected:
            self.selected_type = list(e.control.selected)[0]
            self._render_category_chips()

    def open_for_create(self, default_type: str = "gasto", initial_date: datetime | None = None):
        self.editing_tx_id = None
        self.title_text.value = "Registrar Movimiento"
        self.selected_type = default_type
        self.type_selector.selected = {default_type}
        categories = EXPENSE_CATEGORIES if default_type == "gasto" else INCOME_CATEGORIES
        self.selected_category = list(categories.keys())[0]
        self.selected_payment = PAYMENT_METHODS[0]
        now = datetime.now()
        if initial_date:
            self.selected_date = datetime(
                initial_date.year,
                initial_date.month,
                initial_date.day,
                now.hour,
                now.minute,
                now.second,
            )
        else:
            self.selected_date = now

        self.amount_input.value = ""
        self.amount_input.error_text = None
        self.note_input.value = ""
        self._adjust_modal_size()
        self._update_date_label()
        self._render_category_chips()
        self.page.open(self.dialog)

    def open_for_edit(self, tx: dict):
        self.editing_tx_id = tx["id"]
        self.title_text.value = "Editar Movimiento"
        self.selected_type = tx["type"]
        self.type_selector.selected = {tx["type"]}
        self.selected_category = tx["category"]
        self.amount_input.value = f"{tx['amount']:.2f}"
        self.amount_input.error_text = None

        method, clean_note = parse_payment_and_note(tx.get("note", ""))
        self.selected_payment = method
        self.note_input.value = clean_note

        try:
            self.selected_date = datetime.fromisoformat(str(tx.get("created_at", ""))[:19])
        except Exception:
            self.selected_date = datetime.now()

        self._adjust_modal_size()
        self._update_date_label()
        self._render_category_chips()
        self.page.open(self.dialog)

    def _save(self, e):
        try:
            raw_text = (self.amount_input.value or "").replace(",", ".").strip()
            val = round(float(raw_text), 2)
            if val <= 0:
                self.amount_input.error_text = "El monto debe ser mayor a S/ 0.00"
                self.page.update()
                return
            if val > MAX_TRANSACTION_AMOUNT:
                self.amount_input.error_text = f"Máximo: {CURRENCY_SYMBOL} {MAX_TRANSACTION_AMOUNT:,.2f}"
                self.page.update()
                return
        except (ValueError, AttributeError):
            self.amount_input.error_text = "Ingresa un monto válido (ej. 25.50)"
            self.page.update()
            return

        self.amount_input.error_text = None
        combined_note = format_payment_and_note(self.selected_payment, self.note_input.value or "")
        iso_date = self.selected_date.isoformat()
        self.page.close(self.dialog)

        self.on_save_callback(
            self.editing_tx_id,
            self.selected_type,
            val,
            self.selected_category,
            combined_note,
            iso_date,
        )