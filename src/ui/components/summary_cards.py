import flet as ft
from config.settings import CURRENCY_SYMBOL


def build_summary_cards(
    all_time_balance: float,
    monthly_income: float,
    monthly_expense: float,
    pending_count: int,
    month_label: str,
) -> ft.ResponsiveRow:
    monthly_net = monthly_income - monthly_expense

    def create_card(title: str, amount: float, icon: str, color: str, subtitle: str = "", col_cfg: dict | None = None):
        return ft.Container(
            col=col_cfg or {"xs": 12, "sm": 12, "md": 4},
            padding=15,
            border_radius=16,
            bgcolor="surfaceVariant",
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(
                                title,
                                size=12,
                                weight=ft.FontWeight.W_600,
                                color="onSurfaceVariant",
                                expand=True,
                                no_wrap=True,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Icon(icon, color=color, size=20),
                        ],
                    ),
                    ft.Text(
                        f"{CURRENCY_SYMBOL} {amount:,.2f}",
                        size=21,
                        weight=ft.FontWeight.BOLD,
                        no_wrap=True,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    ft.Text(
                        subtitle,
                        size=11,
                        color="onSurfaceVariant",
                        no_wrap=True,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    )
                    if subtitle
                    else ft.Container(),
                ],
            ),
        )

    sync_status = (
        f"⏳ {pending_count} pendiente(s) de sincronizar"
        if pending_count > 0
        else "☁️ Respaldado y al día"
    )
    net_sign = "+" if monthly_net >= 0 else ""

    return ft.ResponsiveRow(
        spacing=10,
        run_spacing=10,
        controls=[
            create_card(
                "Saldo Disponible Total",
                all_time_balance,
                ft.Icons.ACCOUNT_BALANCE_WALLET,
                "green400" if all_time_balance >= 0 else "red400",
                f"{sync_status} • Neto {month_label}: {net_sign}{CURRENCY_SYMBOL} {monthly_net:,.2f}",
                col_cfg={"xs": 12, "sm": 12, "md": 4},
            ),
            create_card(
                f"Ingresos ({month_label})",
                monthly_income,
                ft.Icons.TRENDING_UP,
                "teal400",
                "Entradas del periodo",
                col_cfg={"xs": 6, "sm": 6, "md": 4},
            ),
            create_card(
                f"Gastos ({month_label})",
                monthly_expense,
                ft.Icons.TRENDING_DOWN,
                "red400",
                "Salidas del periodo",
                col_cfg={"xs": 6, "sm": 6, "md": 4},
            ),
        ],
    )