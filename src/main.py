import flet as ft
from config.settings import THEME_SEED_COLOR
from services.local_storage import LocalStorageService
from services.supabase_service import SupabaseService
from ui.views.dashboard_view import DashboardView

def main(page: ft.Page):
    page.title = "Control de Ingresos y Gastos"
    page.padding = 0
    page.theme_mode = ft.ThemeMode.SYSTEM

    # Oculta cualquier barra de desplazamiento visual en toda la aplicación
    hidden_scroll = ft.ScrollbarTheme(
        thickness=0,
        thumb_visibility=False,
        track_visibility=False,
    )

    page.theme = ft.Theme(
        color_scheme_seed=THEME_SEED_COLOR,
        use_material3=True,
        scrollbar_theme=hidden_scroll,
    )
    page.dark_theme = ft.Theme(
        color_scheme_seed=THEME_SEED_COLOR,
        use_material3=True,
        scrollbar_theme=hidden_scroll,
    )

    page.window.width = 440
    page.window.height = 840

    # Inicialización de servicios Offline-First y restauración de sesión
    local_storage = LocalStorageService(page)
    supabase_service = SupabaseService(local_storage)

    dashboard = DashboardView(page, local_storage, supabase_service)
    page.add(dashboard.build())

if __name__ == "__main__":
    ft.app(target=main)