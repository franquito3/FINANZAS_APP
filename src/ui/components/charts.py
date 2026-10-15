import flet as ft
from config.settings import EXPENSE_CATEGORIES, CURRENCY_SYMBOL

def build_expense_pie_chart(transactions: list[dict]) -> ft.Container:
    expenses = [t for t in transactions if t["type"] == "gasto"]
    total_expense = sum(t["amount"] for t in expenses)

    if total_expense == 0:
        return ft.Container(
            padding=18,
            border_radius=16,
            bgcolor="surfaceVariant",
            height=245,
            alignment=ft.alignment.center,
            content=ft.Column(
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.PIE_CHART_OUTLINE, size=40, color="onSurfaceVariant"),
                    ft.Text("Distribución de Gastos por Sobre", size=15, weight=ft.FontWeight.BOLD),
                    ft.Text("Sin gastos registrados aún", size=13, color="onSurfaceVariant"),
                ],
            ),
        )

    by_cat = {}
    for t in expenses:
        by_cat[t["category"]] = by_cat.get(t["category"], 0) + t["amount"]

    sections = []
    for cat, amount in by_cat.items():
        pct = (amount / total_expense) * 100
        cat_info = EXPENSE_CATEGORIES.get(cat, {"color": "grey"})
        sections.append(
            ft.PieChartSection(
                value=amount,
                title=f"{pct:.0f}%",
                title_style=ft.TextStyle(size=12, weight=ft.FontWeight.BOLD, color="white"),
                color=cat_info["color"],
                radius=55,
            )
        )

    chart = ft.PieChart(
        sections=sections,
        sections_space=3,
        center_space_radius=45,
        expand=True,
    )

    legend = ft.Column(
        spacing=6,
        alignment=ft.MainAxisAlignment.CENTER,
        controls=[
            ft.Row(
                spacing=8,
                controls=[
                    ft.Container(width=12, height=12, border_radius=6, bgcolor=EXPENSE_CATEGORIES.get(cat, {"color": "grey"})["color"]),
                    ft.Text(f"{cat}: {CURRENCY_SYMBOL} {amt:,.2f}", size=12),
                ],
            )
            for cat, amt in by_cat.items()
        ],
    )

    return ft.Container(
        padding=18,
        border_radius=16,
        bgcolor="surfaceVariant",
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Text("Distribución de Gastos por Sobre", size=15, weight=ft.FontWeight.BOLD),
                ft.ResponsiveRow(
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(col={"sm": 12, "md": 6}, height=190, content=chart),
                        ft.Container(col={"sm": 12, "md": 6}, content=legend),
                    ],
                ),
            ],
        ),
    )

def build_cashflow_bar_chart(total_income: float, total_expense: float) -> ft.Container:
    max_y = max(total_income, total_expense, 100) * 1.25

    bar_chart = ft.BarChart(
        interactive=True,
        max_y=max_y,
        border=ft.border.only(bottom=ft.BorderSide(1, "outlineVariant")),
        horizontal_grid_lines=ft.ChartGridLines(interval=max_y / 4, color="outlineVariant", width=0.5),
        bottom_axis=ft.ChartAxis(
            labels=[
                ft.ChartAxisLabel(value=0, label=ft.Container(ft.Text("Ingresos", size=12), padding=5)),
                ft.ChartAxisLabel(value=1, label=ft.Container(ft.Text("Gastos", size=12), padding=5)),
            ],
            labels_size=32,
        ),
        bar_groups=[
            ft.BarChartGroup(
                x=0,
                bar_rods=[
                    ft.BarChartRod(
                        from_y=0,
                        to_y=total_income,
                        width=38,
                        color="teal400",
                        tooltip=f"Ingresos: {CURRENCY_SYMBOL} {total_income:,.2f}",
                        border_radius=ft.border_radius.vertical(top=8),
                    )
                ],
            ),
            ft.BarChartGroup(
                x=1,
                bar_rods=[
                    ft.BarChartRod(
                        from_y=0,
                        to_y=total_expense,
                        width=38,
                        color="red400",
                        tooltip=f"Gastos: {CURRENCY_SYMBOL} {total_expense:,.2f}",
                        border_radius=ft.border_radius.vertical(top=8),
                    )
                ],
            ),
        ],
        expand=True,
    )

    return ft.Container(
        padding=18,
        border_radius=16,
        bgcolor="surfaceVariant",
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Text("Balance Comparativo (S/)", size=15, weight=ft.FontWeight.BOLD),
                ft.Container(height=190, content=bar_chart),
            ],
        ),
    )