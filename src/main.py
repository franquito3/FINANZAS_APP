from urllib.parse import parse_qs, urlparse
import flet as ft
from config.settings import THEME_SEED_COLOR
from services.local_storage import LocalStorageService
from services.supabase_service import SupabaseService
from ui.views.dashboard_view import DashboardView


def main(page: ft.Page):
    page.title = "Mis Finanzas"
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

    page.window.width = 430
    page.window.height = 840

    # Inicialización de servicios Offline-First y restauración de sesión
    local_storage = LocalStorageService(page)
    supabase_service = SupabaseService(local_storage)

    dashboard = DashboardView(page, local_storage, supabase_service)
    page.add(ft.SafeArea(expand=True, content=dashboard.build()))

    # Retorno del login de Google en móvil: misfinanzas://login-callback?code=... o ?status=ok
    def handle_route(route: str | None):
        raw = route or ""
        parsed = urlparse(raw)
        params = parse_qs(parsed.query)
        frag = parse_qs(parsed.fragment)

        if "code" in params:
            dashboard.handle_auth_callback(params["code"][0])
        elif "access_token" in frag or "access_token" in params:
            dashboard.handle_auth_callback(raw)
        elif "status" in params and params["status"][0] == "ok":
            # El servidor loopback local (127.0.0.1:8550) ya procesó el login y nos redirigió de vuelta a la app
            dashboard.refresh_ui()
            if supabase_service.user_id:
                page.run_thread(dashboard._background_sync, True)
        elif "error_description" in params:
            page.open(ft.SnackBar(content=ft.Text(params["error_description"][0])))

    page.on_route_change = lambda e: handle_route(e.route)
    handle_route(page.route)  # por si la app se abrió desde el deep link


if __name__ == "__main__":
    ft.app(target=main)