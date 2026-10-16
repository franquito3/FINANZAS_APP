import calendar
from datetime import datetime
import flet as ft
from config.settings import CURRENCY_SYMBOL

WEEKDAYS_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
MONTH_FULL_NAMES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}


def build_interactive_calendar(
    year: int,
    month: int,
    selected_day: int | None,
    month_transactions: list[dict],
    on_day_click,
    on_prev_month,
    on_next_month,
    on_add_for_date,
) -> ft.Container:
    """Construye un calendario mensual interactivo con indicadores de ingresos y gastos por día."""
    daily_summary: dict[int, dict[str, float]] = {}
    for tx in month_transactions:
        raw_date = str(tx.get("created_at", ""))[:10]
        try:
            d = int(raw_date.split("-")[2])
            if d not in daily_summary:
                daily_summary[d] = {"ingreso": 0.0, "gasto": 0.0, "count": 0}
            daily_summary[d][tx["type"]] = daily_summary[d].get(tx["type"], 0.0) + float(tx["amount"])
            daily_summary[d]["count"] += 1
        except Exception:
            continue

    today = datetime.now()
    is_current_month = today.year == year and today.month == month

    # Encabezado de días de la semana
    weekday_header = ft.Row(
        spacing=4,
        controls=[
            ft.Container(
                expand=True,
                alignment=ft.alignment.center,
                padding=ft.padding.symmetric(vertical=4),
                content=ft.Text(day_name, size=11, weight=ft.FontWeight.BOLD, color="onSurfaceVariant"),
            )
            for day_name in WEEKDAYS_ES
        ],
    )

    cal = calendar.Calendar(firstweekday=0)  # Lunes = 0
    month_weeks = cal.monthdayscalendar(year, month)
    week_rows = []

    for week in month_weeks:
        day_cells = []
        for day_num in week:
            if day_num == 0:
                day_cells.append(ft.Container(expand=True, height=46))
                continue

            info = daily_summary.get(day_num)
            is_selected = selected_day == day_num
            is_today = is_current_month and today.day == day_num

            dots = []
            if info:
                if info["ingreso"] > 0:
                    dots.append(ft.Container(width=6, height=6, border_radius=3, bgcolor="teal400"))
                if info["gasto"] > 0:
                    dots.append(ft.Container(width=6, height=6, border_radius=3, bgcolor="red400"))

            bg_color = "teal400" if is_selected else ("background" if info else "transparent")
            text_color = "white" if is_selected else ("teal400" if is_today else None)
            border_style = (
                ft.border.all(1.5, "teal400")
                if is_today and not is_selected
                else (ft.border.all(1, "outlineVariant") if info and not is_selected else None)
            )

            day_cells.append(
                ft.Container(
                    expand=True,
                    height=46,
                    border_radius=10,
                    bgcolor=bg_color,
                    border=border_style,
                    ink=True,
                    on_click=lambda e, d=day_num: on_day_click(None if selected_day == d else d),
                    content=ft.Column(
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=3,
                        controls=[
                            ft.Text(
                                str(day_num),
                                size=13,
                                weight=ft.FontWeight.BOLD if (is_selected or is_today or info) else ft.FontWeight.NORMAL,
                                color=text_color,
                            ),
                            ft.Row(
                                alignment=ft.MainAxisAlignment.CENTER,
                                spacing=3,
                                controls=dots,
                            )
                            if dots
                            else ft.Container(height=6),
                        ],
                    ),
                )
            )
        week_rows.append(ft.Row(spacing=4, controls=day_cells))

    # Barra de estado del día seleccionado
    if selected_day is not None:
        sel_info = daily_summary.get(selected_day, {"ingreso": 0.0, "gasto": 0.0, "count": 0})
        sel_date_obj = datetime(year, month, selected_day)
        day_banner = ft.Container(
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border_radius=12,
            bgcolor="background",
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        wrap=True,
                        controls=[
                            ft.Row(
                                spacing=6,
                                tight=True,
                                controls=[
                                    ft.Icon(ft.Icons.EVENT_NOTE, size=18, color="teal400"),
                                    ft.Text(
                                        f"{selected_day:02d} de {MONTH_FULL_NAMES[month]} {year}",
                                        weight=ft.FontWeight.BOLD,
                                        size=13,
                                    ),
                                ],
                            ),
                            ft.Row(
                                spacing=6,
                                tight=True,
                                controls=[
                                    ft.TextButton(
                                        "Ver todo el mes",
                                        style=ft.ButtonStyle(padding=ft.padding.symmetric(horizontal=8, vertical=2)),
                                        on_click=lambda e: on_day_click(None),
                                    ),
                                    ft.FilledTonalButton(
                                        "+ Añadir aquí",
                                        height=30,
                                        style=ft.ButtonStyle(padding=ft.padding.symmetric(horizontal=10, vertical=2)),
                                        on_click=lambda e: on_add_for_date(sel_date_obj),
                                    ),
                                ],
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=16,
                        controls=[
                            ft.Text(
                                f"Ingresos: + {CURRENCY_SYMBOL} {sel_info['ingreso']:,.2f}",
                                size=12,
                                color="teal400",
                                weight=ft.FontWeight.W_600,
                            ),
                            ft.Text(
                                f"Gastos: - {CURRENCY_SYMBOL} {sel_info['gasto']:,.2f}",
                                size=12,
                                color="red400",
                                weight=ft.FontWeight.W_600,
                            ),
                        ],
                    ),
                ],
            ),
        )
    else:
        active_days = len(daily_summary)
        day_banner = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            wrap=True,
            controls=[
                ft.Row(
                    spacing=10,
                    tight=True,
                    controls=[
                        ft.Row(
                            spacing=4,
                            tight=True,
                            controls=[
                                ft.Container(width=8, height=8, border_radius=4, bgcolor="teal400"),
                                ft.Text("Ingreso", size=11, color="onSurfaceVariant"),
                            ],
                        ),
                        ft.Row(
                            spacing=4,
                            tight=True,
                            controls=[
                                ft.Container(width=8, height=8, border_radius=4, bgcolor="red400"),
                                ft.Text("Gasto", size=11, color="onSurfaceVariant"),
                            ],
                        ),
                    ],
                ),
                ft.Text(
                    f"Toca un día para filtrar ({active_days} días con actividad)",
                    size=11,
                    color="onSurfaceVariant",
                ),
            ],
        )

    return ft.Container(
        padding=14,
        border_radius=16,
        bgcolor="surfaceVariant",
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.IconButton(
                            icon=ft.Icons.CHEVRON_LEFT,
                            tooltip="Mes anterior",
                            on_click=on_prev_month,
                        ),
                        ft.Column(
                            spacing=0,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Text(
                                    f"{MONTH_FULL_NAMES[month]} {year}",
                                    size=16,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    f"{len(month_transactions)} movimientos en el mes",
                                    size=11,
                                    color="onSurfaceVariant",
                                ),
                            ],
                        ),
                        ft.IconButton(
                            icon=ft.Icons.CHEVRON_RIGHT,
                            tooltip="Mes siguiente",
                            on_click=on_next_month,
                        ),
                    ],
                ),
                weekday_header,
                ft.Column(spacing=4, controls=week_rows),
                day_banner,
            ],
        ),
    )
