import flet as ft
from config.settings import EXPENSE_CATEGORIES, INCOME_CATEGORIES, CURRENCY_SYMBOL, MAX_TRANSACTION_AMOUNT

class TransactionModal:
    def __init__(self, page: ft.Page, on_save_callback):
        self.page = page
        self.on_save_callback = on_save_callback
        self.editing_tx_id: str | None = None
        self.selected_type = "gasto"
        self.selected_category = list(EXPENSE_CATEGORIES.keys())[0]

        self.title_text = ft.Text("Nuevo Movimiento", weight=ft.FontWeight.BOLD)
        self.amount_input = ft.TextField(
            label=f"Monto ({CURRENCY_SYMBOL})",
            prefix_text=f"{CURRENCY_SYMBOL} ",
            keyboard_type=ft.KeyboardType.NUMBER,
            autofocus=True,
            text_size=20,
            border_radius=12,
        )
        self.note_input = ft.TextField(
            label="Nota o detalle (opcional)",
            max_length=90,
            border_radius=12,
        )
        self.category_chips_container = ft.Row(wrap=True, spacing=8, run_spacing=8)

        self.type_selector = ft.SegmentedButton(
            selected={"gasto"},
            allow_multiple_selection=False,
            on_change=self._on_type_change,
            segments=[
                ft.Segment(value="gasto", label=ft.Text("Gasto"), icon=ft.Icon(ft.Icons.REMOVE_CIRCLE_OUTLINE)),
                ft.Segment(value="ingreso", label=ft.Text("Ingreso"), icon=ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE)),
            ],
        )

        self.dialog = ft.AlertDialog(
            modal=True,
            title=self.title_text,
            content=ft.Container(
                width=360,
                content=ft.Column(
                    tight=True,
                    spacing=14,
                    controls=[
                        self.type_selector,
                        self.amount_input,
                        ft.Text("Categoría:", size=13, weight=ft.FontWeight.W_500),
                        self.category_chips_container,
                        self.note_input,
                    ],
                ),
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.page.close(self.dialog)),
                ft.FilledButton("Guardar", icon=ft.Icons.CHECK, on_click=self._save),
            ],
        )

    def _render_category_chips(self):
        categories = EXPENSE_CATEGORIES if self.selected_type == "gasto" else INCOME_CATEGORIES
        if self.selected_category not in categories:
            self.selected_category = list(categories.keys())[0]

        self.category_chips_container.controls.clear()
        for cat_name, meta in categories.items():
            self.category_chips_container.controls.append(
                ft.Chip(
                    label=ft.Text(cat_name, size=12),
                    leading=ft.Icon(meta["icon"], size=16, color=meta["color"]),
                    selected=(self.selected_category == cat_name),
                    on_select=lambda e, c=cat_name: self._select_cat(c),
                )
            )
        self.page.update()

    def _select_cat(self, cat_name: str):
        self.selected_category = cat_name
        self._render_category_chips()

    def _on_type_change(self, e):
        self.selected_type = list(e.control.selected)[0]
        self._render_category_chips()

    def open_for_create(self, default_type: str = "gasto"):
        self.editing_tx_id = None
        self.title_text.value = "Registrar Movimiento"
        self.selected_type = default_type
        self.type_selector.selected = {default_type}
        categories = EXPENSE_CATEGORIES if default_type == "gasto" else INCOME_CATEGORIES
        self.selected_category = list(categories.keys())[0]
        self.amount_input.value = ""
        self.amount_input.error_text = None
        self.note_input.value = ""
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
        self.note_input.value = tx.get("note", "")
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
                self.amount_input.error_text = f"Monto máximo permitido: {CURRENCY_SYMBOL} {MAX_TRANSACTION_AMOUNT:,.2f}"
                self.page.update()
                return
        except (ValueError, AttributeError):
            self.amount_input.error_text = "Ingresa un número válido (ej. 25.50)"
            self.page.update()
            return

        self.amount_input.error_text = None
        clean_note = (self.note_input.value or "").strip()[:90]
        self.page.close(self.dialog)

        self.on_save_callback(
            self.editing_tx_id,
            self.selected_type,
            val,
            self.selected_category,
            clean_note,
        )