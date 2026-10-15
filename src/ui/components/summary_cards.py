import flet as ft
from config.settings import CURRENCY_SYMBOL

def build_summary_cards(
    all_time_balance: float,
    monthly_income: float,
    monthly_expense: float,
    pending_count: int,
    month_label: str,
) -> ft.ResponsiveRow:

    def create_card(title: str, amount: float, icon: str, color: str, subtitle: str = ""):
        return ft.Container(
            col={"sm": 12, "md": 4},
            padding=18,
            border_radius=16,
            bgcolor="surfaceVariant",
            content=ft.Column(
                spacing=6,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(title, size=13, weight=ft.FontWeight.W_500, color="onSurfaceVariant"),
                            ft.Icon(icon, color=color, size=22),
                        ],
                    ),
                    ft.Text(f"{CURRENCY_SYMBOL} {amount:,.2f}", size=24, weight=ft.FontWeight.BOLD),
                    ft.Text(subtitle, size=11, color="onSurfaceVariant") if subtitle else ft.Container(),
                ],
            ),
        )

    sync_status = (
        f"⏳ {pending_count} cambios por sincronizar"
        if pending_count > 0
        else "☁️ Respaldado y al día"
    )

    return ft.ResponsiveRow(
        spacing=12,
        run_spacing=12,
        controls=[
            create_card("Saldo Disponible Total", all_time_balance, ft.Icons.ACCOUNT_BALANCE_WALLET, "green400", sync_status),
            create_card(f"Ingresos ({month_label})", monthly_income, ft.Icons.TRENDING_UP, "teal400", "Acumulado del mes actual"),
            create_card(f"Gastos ({month_label})", monthly_expense, ft.Icons.TRENDING_DOWN, "red400", "Salidas del mes actual"),
        ],
    )