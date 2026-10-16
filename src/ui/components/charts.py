import flet as ft
from config.settings import CURRENCY_SYMBOL, EXPENSE_CATEGORIES


def build_expense_pie_chart(transactions: list[dict]) -> ft.Container:
    expenses = [t for t in transactions if t["type"] == "gasto"]
    total_expense = sum(t["amount"] for t in expenses)

    if total_expense == 0:
        return ft.Container(
            padding=16,
            border_radius=16,
            bgcolor="surfaceVariant",
            height=210,
            alignment=ft.alignment.center,
            content=ft.Column(
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.PIE_CHART_OUTLINE, size=36, color="onSurfaceVariant"),
                    ft.Text("Distribución de Gastos por Categoría", size=14, weight=ft.FontWeight.BOLD),
                    ft.Text("Sin gastos registrados en este periodo", size=12, color="onSurfaceVariant"),
                ],
            ),
        )

    by_cat: dict[str, float] = {}
    for t in expenses:
        by_cat[t["category"]] = by_cat.get(t["category"], 0.0) + float(t["amount"])

    sorted_cats = sorted(by_cat.items(), key=lambda x: x[1], reverse=True)

    sections = []
    for cat, amount in sorted_cats:
        pct = (amount / total_expense) * 100
        cat_info = EXPENSE_CATEGORIES.get(cat, {"color": "grey"})
        sections.append(
            ft.PieChartSection(
                value=amount,
                title=f"{pct:.0f}%" if pct >= 8 else "",
                title_style=ft.TextStyle(size=11, weight=ft.FontWeight.BOLD, color="white"),
                color=cat_info["color"],
                radius=50,
            )
        )

    chart = ft.PieChart(
        sections=sections,
        sections_space=2,
        center_space_radius=40,
        expand=True,
    )

    legend = ft.Column(
        spacing=6,
        alignment=ft.MainAxisAlignment.CENTER,
        controls=[
            ft.Row(
                spacing=8,
                controls=[
                    ft.Container(
                        width=10,
                        height=10,
                        border_radius=5,
                        bgcolor=EXPENSE_CATEGORIES.get(cat, {"color": "grey"})["color"],
                    ),
                    ft.Text(
                        cat,
                        size=12,
                        expand=True,
                        no_wrap=True,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    ft.Text(
                        f"{CURRENCY_SYMBOL} {amt:,.2f}",
                        size=12,
                        weight=ft.FontWeight.W_600,
                    ),
                ],
            )
            for cat, amt in sorted_cats
        ],
    )

    return ft.Container(
        padding=16,
        border_radius=16,
        bgcolor="surfaceVariant",
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Text("Distribución de Gastos por Categoría", size=14, weight=ft.FontWeight.BOLD),
                ft.ResponsiveRow(
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(col={"xs": 12, "sm": 12, "md": 6}, height=175, content=chart),
                        ft.Container(col={"xs": 12, "sm": 12, "md": 6}, content=legend),
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
            labels_size=30,
        ),
        bar_groups=[
            ft.BarChartGroup(
                x=0,
                bar_rods=[
                    ft.BarChartRod(
                        from_y=0,
                        to_y=total_income,
                        width=36,
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
                        width=36,
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
        padding=16,
        border_radius=16,
        bgcolor="surfaceVariant",
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Text(f"Balance Comparativo ({CURRENCY_SYMBOL})", size=14, weight=ft.FontWeight.BOLD),
                ft.Container(height=175, content=bar_chart),
            ],
        ),
    )


def build_budget_50_30_20_card(transactions: list[dict], monthly_income: float) -> ft.Container:
    """Muestra el cumplimiento de la Regla Financiera 50/30/20 según los ingresos del mes."""
    groups = {
        "Necesidades (50%)": {"pct": 0.50, "color": "blue400", "spent": 0.0},
        "Deseos (30%)": {"pct": 0.30, "color": "purple400", "spent": 0.0},
        "Futuro (20%)": {"pct": 0.20, "color": "green400", "spent": 0.0},
    }

    for tx in transactions:
        if tx["type"] == "gasto":
            cat_meta = EXPENSE_CATEGORIES.get(tx["category"], {})
            grp = cat_meta.get("group", "Deseos (30%)")
            if grp in groups:
                groups[grp]["spent"] += float(tx["amount"])

    base_income = monthly_income if monthly_income > 0 else sum(g["spent"] for g in groups.values())
    rows = []

    for label, meta in groups.items():
        spent = meta["spent"]
        target = base_income * meta["pct"] if monthly_income > 0 else 0.0
        ratio = min(spent / target, 1.0) if target > 0 else (min(spent / max(base_income, 1.0), 1.0) if base_income > 0 else 0.0)
        over_budget = target > 0 and spent > target
        bar_color = "red400" if over_budget else meta["color"]

        subtitle_right = (
            f"{CURRENCY_SYMBOL} {spent:,.2f} / {CURRENCY_SYMBOL} {target:,.2f}"
            if monthly_income > 0
            else f"{CURRENCY_SYMBOL} {spent:,.2f}"
        )

        rows.append(
            ft.Column(
                spacing=4,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(label, size=12, weight=ft.FontWeight.W_600),
                            ft.Text(
                                subtitle_right,
                                size=11,
                                color="red400" if over_budget else "onSurfaceVariant",
                                weight=ft.FontWeight.BOLD if over_budget else ft.FontWeight.NORMAL,
                            ),
                        ],
                    ),
                    ft.ProgressBar(value=ratio, color=bar_color, bgcolor="background", bar_height=7, border_radius=4),
                ],
            )
        )

    helper = (
        "Basado en tus ingresos registrados este mes"
        if monthly_income > 0
        else "Registra tus ingresos del mes para calcular tus topes sugeridos 50/30/20"
    )

    return ft.Container(
        padding=16,
        border_radius=16,
        bgcolor="surfaceVariant",
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text("Presupuesto Regla 50 / 30 / 20", size=14, weight=ft.FontWeight.BOLD),
                        ft.Icon(ft.Icons.ACCOUNT_BALANCE_OUTLINED, size=18, color="teal400"),
                    ],
                ),
                ft.Text(helper, size=11, color="onSurfaceVariant"),
                *rows,
            ],
        ),
    )