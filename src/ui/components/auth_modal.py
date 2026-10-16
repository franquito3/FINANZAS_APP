import flet as ft


class AuthModal:
    """Modal de Autenticación y Respaldo en la Nube compatible con APK Android y Escritorio."""

    def __init__(self, page: ft.Page, supabase_service, on_auth_changed):
        self.page = page
        self.supabase_service = supabase_service
        self.on_auth_changed = on_auth_changed
        self.mode = "login"  # "login" o "signup"

        self.mode_selector = ft.SegmentedButton(
            selected={"login"},
            allow_multiple_selection=False,
            on_change=self._on_mode_change,
            segments=[
                ft.Segment(value="login", label=ft.Text("Iniciar Sesión", size=12), icon=ft.Icon(ft.Icons.LOGIN, size=16)),
                ft.Segment(value="signup", label=ft.Text("Crear Cuenta", size=12), icon=ft.Icon(ft.Icons.PERSON_ADD, size=16)),
            ],
        )

        self.email_input = ft.TextField(
            label="Correo electrónico",
            keyboard_type=ft.KeyboardType.EMAIL,
            prefix_icon=ft.Icons.EMAIL_OUTLINED,
            border_radius=12,
            text_size=14,
            content_padding=ft.padding.symmetric(horizontal=14, vertical=10),
        )

        self.password_input = ft.TextField(
            label="Contraseña (mín. 6 caracteres)",
            password=True,
            can_reveal_password=True,
            prefix_icon=ft.Icons.LOCK_OUTLINE,
            border_radius=12,
            text_size=14,
            content_padding=ft.padding.symmetric(horizontal=14, vertical=10),
            on_submit=self._submit_email_auth,
        )

        self.status_text = ft.Text("", size=12, color="red400", visible=False)
        self.loading_bar = ft.ProgressBar(visible=False, color="teal400")

        self.submit_email_btn = ft.FilledButton(
            text="Ingresar con Correo",
            icon=ft.Icons.ARROW_FORWARD,
            expand=True,
            height=42,
            on_click=self._submit_email_auth,
        )

        self.google_btn = ft.OutlinedButton(
            text="Continuar con Google",
            icon=ft.Icons.ACCOUNT_CIRCLE,
            expand=True,
            height=42,
            on_click=self._start_google_oauth,
        )

        self.body_container = ft.Container(width=330, height=340)

        self.dialog = ft.AlertDialog(
            modal=True,
            inset_padding=ft.padding.symmetric(horizontal=14, vertical=18),
            title_padding=ft.padding.only(left=18, top=16, right=18, bottom=4),
            content_padding=ft.padding.only(left=18, top=8, right=18, bottom=12),
            actions_padding=ft.padding.only(left=12, top=0, right=16, bottom=12),
            title=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.Icon(ft.Icons.CLOUD_SYNC, color="teal400", size=22),
                            ft.Text("Cuenta y Nube", weight=ft.FontWeight.BOLD, size=17),
                        ],
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CLOSE,
                        icon_size=20,
                        on_click=lambda e: self.page.close(self.dialog),
                    ),
                ],
            ),
            content=self.body_container,
        )

    def _adjust_size(self):
        page_h = self.page.height or 760
        page_w = self.page.width or 380
        self.body_container.width = min(max(page_w - 56, 260), 390)
        if self.supabase_service.user_email:
            self.body_container.height = 210
        else:
            self.body_container.height = min(max(int(page_h * 0.48), 270), 370)

    def _on_mode_change(self, e):
        if e.control.selected:
            self.mode = list(e.control.selected)[0]
            self.submit_email_btn.text = (
                "Ingresar con Correo" if self.mode == "login" else "Registrar Cuenta Gratis"
            )
            self.status_text.visible = False
            self.page.update()

    def open(self):
        self.status_text.visible = False
        self.loading_bar.visible = False
        self._adjust_size()
        self._build_content()
        self.page.open(self.dialog)

    def _build_content(self):
        if self.supabase_service.user_email:
            self.body_container.content = ft.Column(
                scroll=ft.ScrollMode.AUTO,
                tight=True,
                spacing=12,
                controls=[
                    ft.Container(
                        padding=14,
                        border_radius=12,
                        bgcolor="surfaceVariant",
                        content=ft.Row(
                            spacing=12,
                            controls=[
                                ft.Icon(ft.Icons.VERIFIED_USER, color="teal400", size=28),
                                ft.Column(
                                    spacing=2,
                                    expand=True,
                                    controls=[
                                        ft.Text("Sesión activa en la nube", size=12, color="onSurfaceVariant"),
                                        ft.Text(
                                            self.supabase_service.user_email,
                                            weight=ft.FontWeight.BOLD,
                                            size=14,
                                            no_wrap=True,
                                            overflow=ft.TextOverflow.ELLIPSIS,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ),
                    ft.Text(
                        "Tus movimientos están vinculados a tu cuenta y se sincronizan automáticamente cuando tienes internet.",
                        size=12,
                        color="onSurfaceVariant",
                    ),
                    ft.Row(
                        spacing=10,
                        controls=[
                            ft.FilledTonalButton(
                                "Sincronizar ahora",
                                icon=ft.Icons.SYNC,
                                expand=True,
                                on_click=self._sync_now,
                            ),
                            ft.FilledButton(
                                "Cerrar Sesión",
                                icon=ft.Icons.LOGOUT,
                                bgcolor="red400",
                                color="white",
                                on_click=self._logout,
                            ),
                        ],
                    ),
                ],
            )
        else:
            self.body_container.content = ft.Column(
                scroll=ft.ScrollMode.AUTO,
                tight=True,
                spacing=10,
                controls=[
                    ft.Text(
                        "Inicia sesión con tu correo (recomendado en APK) o con Google para respaldar tus finanzas.",
                        size=12,
                        color="onSurfaceVariant",
                    ),
                    ft.Container(alignment=ft.alignment.center, content=self.mode_selector),
                    self.email_input,
                    self.password_input,
                    self.loading_bar,
                    self.status_text,
                    ft.Row(controls=[self.submit_email_btn]),
                    ft.Divider(height=8),
                    ft.Row(controls=[self.google_btn]),
                ],
            )

    def _submit_email_auth(self, e):
        email = (self.email_input.value or "").strip()
        password = self.password_input.value or ""
        if not email or not password:
            self.status_text.value = "Completa tu correo y contraseña."
            self.status_text.color = "red400"
            self.status_text.visible = True
            self.page.update()
            return

        self.loading_bar.visible = True
        self.status_text.visible = False
        self.page.update()

        def _worker():
            if self.mode == "login":
                ok, msg = self.supabase_service.sign_in_with_password(email, password)
            else:
                ok, msg = self.supabase_service.sign_up_with_password(email, password)

            self.loading_bar.visible = False
            if ok and self.supabase_service.user_id:
                self.password_input.value = ""
                self.page.close(self.dialog)
                self.on_auth_changed(msg)
            else:
                self.status_text.value = msg
                self.status_text.color = "teal400" if ok else "red400"
                self.status_text.visible = True
                self.page.update()

        self.page.run_thread(_worker)

    def _start_google_oauth(self, e):
        is_mobile = self.page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS)

        def _on_success():
            self.page.close(self.dialog)
            self.on_auth_changed("¡Cuenta de Google conectada!")

        url = self.supabase_service.start_google_login(_on_success, is_mobile=is_mobile)
        if url:
            self.status_text.value = "Completando inicio de sesión en el navegador..."
            self.status_text.color = "teal400"
            self.status_text.visible = True
            self.page.update()
            self.page.launch_url(url)
        else:
            self.status_text.value = "Revisa SUPABASE_URL y SUPABASE_KEY en settings.py"
            self.status_text.color = "red400"
            self.status_text.visible = True
            self.page.update()

    def _sync_now(self, e):
        self.page.close(self.dialog)
        self.on_auth_changed("Sincronizando con la nube...")

    def _logout(self, e):
        self.supabase_service.logout()
        self.page.close(self.dialog)
        self.on_auth_changed("Sesión cerrada correctamente", sync=False)
