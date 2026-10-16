import base64
import hashlib
import json
import os
import secrets
import ssl
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

from config.settings import SUPABASE_KEY, SUPABASE_URL
from services.local_storage import LocalStorageService

# Asegurar certificados SSL válidos en Android / iOS / Escritorio
try:
    import certifi

    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _SSL_CONTEXT = ssl.create_default_context()

# Redirecciones OAuth:
# Usamos http://localhost:8550 tanto en escritorio como en Android porque el proceso Python
# en el APK comparte loopback (127.0.0.1) con el navegador del teléfono y ya está autorizado en Supabase.
# Al finalizar, el servidor local redirige automáticamente al deep link misfinanzas://login-callback.
LOOPBACK_PORT = 8550
DESKTOP_REDIRECT_URL = f"http://localhost:{LOOPBACK_PORT}"
MOBILE_DEEP_LINK_URL = "misfinanzas://login-callback"


class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True


class FileAuthStorage:
    """Almacenamiento persistente en disco para el code_verifier PKCE y estado OAuth."""

    def __init__(self):
        base_dir = os.getenv("FLET_APP_STORAGE_DATA") or tempfile.gettempdir()
        os.makedirs(base_dir, exist_ok=True)
        self._path = os.path.join(base_dir, "supabase_auth_storage.json")
        self._lock = threading.Lock()

    def _read(self) -> dict:
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write(self, data: dict):
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass

    def get_item(self, key: str):
        with self._lock:
            return self._read().get(key)

    def set_item(self, key: str, value: str):
        with self._lock:
            data = self._read()
            data[key] = value
            self._write(data)

    def remove_item(self, key: str):
        with self._lock:
            data = self._read()
            if key in data:
                del data[key]
                self._write(data)


class SupabaseService:
    """Cliente Supabase 100% compatible con Android APK y Escritorio (sin dependencias binarias frágiles)."""

    PKCE_VERIFIER_KEY = "pkce_code_verifier"

    def __init__(self, local_storage: LocalStorageService):
        self.local_storage = local_storage
        self.file_storage = FileAuthStorage()
        self.base_url = (SUPABASE_URL or "").rstrip("/")
        self.api_key = (SUPABASE_KEY or "").strip()
        self.is_configured = bool(self.base_url and self.api_key and "tu-proyecto" not in self.base_url)

        self.user_id: str | None = None
        self.user_email: str | None = None
        self.access_token: str | None = None
        self.refresh_token: str | None = None
        self.last_error: str | None = None
        self._sync_lock = threading.Lock()
        self._active_oauth_server: ReusableHTTPServer | None = None

        if self.is_configured:
            self._restore_saved_session()

    # --- Cliente HTTP REST directo con soporte SSL en Android ---
    def _request(
        self,
        method: str,
        path: str,
        body: dict | list | None = None,
        token: str | None = None,
        extra_headers: dict | None = None,
        timeout: int = 15,
    ) -> tuple[int, dict | list | str | None]:
        url = f"{self.base_url}{path}"
        headers = {
            "apikey": self.api_key,
            "Authorization": f"Bearer {token or self.access_token or self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)

        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, context=_SSL_CONTEXT, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                if not raw:
                    return resp.status, None
                try:
                    return resp.status, json.loads(raw)
                except Exception:
                    return resp.status, raw
        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode("utf-8")
                parsed_err = json.loads(err_body)
                return e.code, parsed_err
            except Exception:
                return e.code, {"message": err_body or str(e)}
        except Exception as e:
            # Fallback sin verificación estricta solo si el dispositivo Android tiene un CA store corrupto
            if "CERTIFICATE_VERIFY_FAILED" in str(e):
                try:
                    unverified_ctx = ssl._create_unverified_context()
                    with urllib.request.urlopen(req, context=unverified_ctx, timeout=timeout) as resp:
                        raw = resp.read().decode("utf-8")
                        return resp.status, json.loads(raw) if raw else None
                except Exception as inner_e:
                    raise inner_e
            raise e

    def _extract_error_message(self, payload: dict | list | str | None, fallback: str) -> str:
        if isinstance(payload, dict):
            msg = (
                payload.get("msg")
                or payload.get("error_description")
                or payload.get("message")
                or payload.get("error")
            )
            if msg:
                if "Invalid login credentials" in str(msg):
                    return "Correo o contraseña incorrectos."
                if "Email not confirmed" in str(msg):
                    return "Confirma tu correo electrónico antes de iniciar sesión (revisa tu bandeja de entrada)."
                if "User already registered" in str(msg):
                    return "Este correo ya está registrado. Usa la pestaña 'Iniciar Sesión'."
                return str(msg)
        return fallback

    # --- Gestión de Sesión ---
    def _apply_and_save_auth_payload(self, data: dict) -> bool:
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        user = data.get("user") or {}
        user_id = user.get("id") or data.get("user_id")
        email = user.get("email") or data.get("email")

        if not access_token or not user_id:
            return False

        self.access_token = access_token
        self.refresh_token = refresh_token
        self.user_id = user_id
        self.user_email = email or "Usuario conectado"

        self.local_storage.save_session({
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "user_id": self.user_id,
            "email": self.user_email,
        })
        return True

    def _restore_saved_session(self):
        saved = self.local_storage.get_session()
        if not saved:
            return
        self.access_token = saved.get("access_token")
        self.refresh_token = saved.get("refresh_token")
        self.user_id = saved.get("user_id")
        self.user_email = saved.get("email")

    def _ensure_valid_session(self) -> bool:
        saved = self.local_storage.get_session()
        if not saved or not self.is_configured:
            return False

        self.access_token = saved.get("access_token")
        self.refresh_token = saved.get("refresh_token")
        self.user_id = saved.get("user_id")
        self.user_email = saved.get("email")

        # Verificar si el access_token actual funciona o refrescarlo
        if self.refresh_token:
            try:
                status, data = self._request(
                    "POST",
                    "/auth/v1/token?grant_type=refresh_token",
                    body={"refresh_token": self.refresh_token},
                    token=self.api_key,
                    timeout=10,
                )
                if status == 200 and isinstance(data, dict):
                    self._apply_and_save_auth_payload(data)
                    return True
            except Exception:
                # Si estamos sin internet, mantenemos la sesión en caché
                pass
        return bool(self.access_token and self.user_id)

    def logout(self):
        if self.is_configured and self.access_token:
            try:
                self._request("POST", "/auth/v1/logout", token=self.access_token, timeout=5)
            except Exception:
                pass
        self.user_id = None
        self.user_email = None
        self.access_token = None
        self.refresh_token = None
        self.local_storage.clear_session()

    # --- Autenticación Nativa con Correo y Contraseña (funciona dentro del APK sin navegador) ---
    def sign_in_with_password(self, email: str, password: str) -> tuple[bool, str]:
        if not self.is_configured:
            return False, "Supabase no está configurado en settings.py"
        clean_email = (email or "").strip()
        if not clean_email or not password:
            return False, "Ingresa tu correo y contraseña."

        try:
            status, data = self._request(
                "POST",
                "/auth/v1/token?grant_type=password",
                body={"email": clean_email, "password": password},
                token=self.api_key,
            )
            if status == 200 and isinstance(data, dict) and self._apply_and_save_auth_payload(data):
                return True, f"¡Bienvenido, {self.user_email}!"
            return False, self._extract_error_message(data, "No se pudo iniciar sesión.")
        except Exception as e:
            return False, f"Error de red al conectar con Supabase: {e}"

    def sign_up_with_password(self, email: str, password: str) -> tuple[bool, str]:
        if not self.is_configured:
            return False, "Supabase no está configurado en settings.py"
        clean_email = (email or "").strip()
        if not clean_email or len(password or "") < 6:
            return False, "Ingresa un correo válido y una contraseña de al menos 6 caracteres."

        try:
            status, data = self._request(
                "POST",
                "/auth/v1/signup",
                body={"email": clean_email, "password": password},
                token=self.api_key,
            )
            if status in (200, 201) and isinstance(data, dict):
                # Si Supabase devuelve sesión directa (autoconfirm activado)
                if self._apply_and_save_auth_payload(data):
                    return True, f"¡Cuenta creada y conectada ({self.user_email})!"
                # Si requiere confirmación por email o devuelve el objeto user en raíz
                if data.get("id") or (isinstance(data.get("user"), dict) and data["user"].get("id")):
                    return (
                        True,
                        "¡Registro exitoso! Revisa tu correo electrónico para confirmar tu cuenta y luego inicia sesión.",
                    )
            return False, self._extract_error_message(data, "No se pudo crear la cuenta.")
        except Exception as e:
            return False, f"Error de red al registrar cuenta: {e}"

    # --- Autenticación con Google OAuth (PKCE + Servidor Local Loopback + Deep Link) ---
    def _generate_pkce_pair(self) -> tuple[str, str]:
        verifier = secrets.token_urlsafe(48)
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
        self.file_storage.set_item(self.PKCE_VERIFIER_KEY, verifier)
        try:
            self.local_storage.page.client_storage.set(self.PKCE_VERIFIER_KEY, verifier)
        except Exception:
            pass
        return verifier, challenge

    def _get_saved_pkce_verifier(self) -> str | None:
        v = self.file_storage.get_item(self.PKCE_VERIFIER_KEY)
        if v:
            return v
        try:
            return self.local_storage.page.client_storage.get(self.PKCE_VERIFIER_KEY)
        except Exception:
            return None

    def start_google_login(self, on_login_success, is_mobile: bool = False) -> str | None:
        """Inicia el flujo OAuth con Google.
        En móvil usa el deep link registrado en Android (misfinanzas://login-callback).
        En escritorio usa el servidor local loopback (http://localhost:8550)."""
        if not self.is_configured:
            return None
        try:
            _, challenge = self._generate_pkce_pair()
            redirect_to = MOBILE_DEEP_LINK_URL if is_mobile else DESKTOP_REDIRECT_URL

            # En escritorio levantamos el listener local; en móvil el retorno llega vía deep link a la app
            if not is_mobile:
                self._listen_for_oauth_callback(on_login_success, is_mobile=False)

            params = urllib.parse.urlencode({
                "provider": "google",
                "redirect_to": redirect_to,
                "code_challenge": challenge,
                "code_challenge_method": "s256",
            })
            return f"{self.base_url}/auth/v1/authorize?{params}"
        except Exception as e:
            self.last_error = str(e)
            return None

    def complete_login_with_code(self, auth_code_or_url: str) -> tuple[bool, str]:
        """Intercambia el código OAuth (PKCE) o URL de retorno por una sesión válida."""
        if not self.is_configured:
            return False, "Supabase no está configurado"

        raw = (auth_code_or_url or "").strip()
        if not raw:
            return False, "Código de autorización vacío"

        # Si el usuario pegó la URL completa (ej. http://localhost:8550/?code=...)
        if "code=" in raw or raw.startswith("http") or raw.startswith("misfinanzas://"):
            parsed = urllib.parse.urlparse(raw)
            qs = urllib.parse.parse_qs(parsed.query)
            frag = urllib.parse.parse_qs(parsed.fragment)
            if "access_token" in frag:
                return self.complete_login_with_tokens(
                    frag["access_token"][0],
                    frag.get("refresh_token", [""])[0],
                )
            if "code" in qs:
                raw = qs["code"][0]

        verifier = self._get_saved_pkce_verifier() or ""
        try:
            status, data = self._request(
                "POST",
                "/auth/v1/token?grant_type=pkce",
                body={"auth_code": raw, "code_verifier": verifier},
                token=self.api_key,
            )
            if status == 200 and isinstance(data, dict) and self._apply_and_save_auth_payload(data):
                return True, f"Sesión iniciada como {self.user_email}"
            return False, self._extract_error_message(data, "El código de Google expiró o no es válido.")
        except Exception as e:
            return False, f"Error de conexión al validar sesión: {e}"

    def complete_login_with_tokens(self, access_token: str, refresh_token: str = "") -> tuple[bool, str]:
        """Completa el inicio de sesión cuando Supabase devuelve access_token directo (flujo implícito)."""
        if not access_token:
            return False, "Token vacío"
        try:
            status, user_data = self._request("GET", "/auth/v1/user", token=access_token)
            if status == 200 and isinstance(user_data, dict) and user_data.get("id"):
                payload = {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "user": user_data,
                }
                if self._apply_and_save_auth_payload(payload):
                    return True, f"Sesión iniciada como {self.user_email}"
            return False, "No se pudo obtener el perfil del usuario."
        except Exception as e:
            return False, f"Error al verificar token: {e}"

    def _listen_for_oauth_callback(self, on_login_success, is_mobile: bool = False):
        service = self
        auth_completed = threading.Event()

        # Cerrar cualquier servidor anterior que haya quedado abierto
        if self._active_oauth_server is not None:
            try:
                self._active_oauth_server.server_close()
            except Exception:
                pass
            self._active_oauth_server = None

        class OAuthCallbackHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def _send_html(self, status_code: int, html: str):
                self.send_response(status_code)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(html.encode("utf-8"))

            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                if parsed.path == "/favicon.ico":
                    self.send_response(204)
                    self.end_headers()
                    return

                params = urllib.parse.parse_qs(parsed.query)

                # Caso 1: Llega ?code=... (Flujo PKCE)
                if "code" in params:
                    auth_code = params["code"][0]
                    ok, msg = service.complete_login_with_code(auth_code)
                    if ok:
                        auth_completed.set()
                        return_btn = (
                            f'<a href="{MOBILE_DEEP_LINK_URL}?status=ok" '
                            'style="display:inline-block;margin-top:20px;padding:14px 28px;background:#10B981;'
                            'color:#fff;text-decoration:none;border-radius:12px;font-weight:bold;">'
                            "Volver a la App Mis Finanzas</a>"
                            f'<script>setTimeout(function(){{ window.location.href = "{MOBILE_DEEP_LINK_URL}?status=ok"; }}, 600);</script>'
                            if is_mobile
                            else "<script>setTimeout(function(){ window.close(); }, 1200);</script>"
                        )
                        html = f"""<!DOCTYPE html>
                        <html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head>
                        <body style="font-family:sans-serif;text-align:center;padding:60px 20px;background:#0f172a;color:#f8fafc;">
                        <div style="max-width:380px;margin:0 auto;background:#1e293b;padding:28px;border-radius:18px;">
                        <h2 style="color:#10B981;margin-top:0;">¡Cuenta conectada con éxito!</h2>
                        <p style="color:#cbd5e1;">{msg}</p>
                        <p style="color:#94a3b8;font-size:14px;">Ya puedes regresar a la aplicación Mis Finanzas.</p>
                        {return_btn}
                        </div></body></html>"""
                        self._send_html(200, html)
                        on_login_success()
                        return
                    else:
                        auth_completed.set()
                        self._send_html(
                            400,
                            f"<html><body style='font-family:sans-serif;background:#0f172a;color:#fff;text-align:center;padding:40px;'>"
                            f"<h3 style='color:#f87171;'>No se pudo completar el inicio de sesión</h3><p>{msg}</p></body></html>",
                        )
                        return

                # Caso 2: Llega ?access_token=... redirigido desde el script que lee window.location.hash
                if "access_token" in params:
                    ok, msg = service.complete_login_with_tokens(
                        params["access_token"][0],
                        params.get("refresh_token", [""])[0],
                    )
                    auth_completed.set()
                    if ok:
                        return_btn = (
                            f'<a href="{MOBILE_DEEP_LINK_URL}?status=ok" '
                            'style="display:inline-block;margin-top:20px;padding:14px 28px;background:#10B981;'
                            'color:#fff;text-decoration:none;border-radius:12px;font-weight:bold;">'
                            "Volver a la App Mis Finanzas</a>"
                            f'<script>setTimeout(function(){{ window.location.href = "{MOBILE_DEEP_LINK_URL}?status=ok"; }}, 600);</script>'
                            if is_mobile
                            else "<script>setTimeout(function(){ window.close(); }, 1200);</script>"
                        )
                        self._send_html(
                            200,
                            f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1'></head>"
                            f"<body style='font-family:sans-serif;text-align:center;padding:60px 20px;background:#0f172a;color:#fff;'>"
                            f"<h2 style='color:#10B981;'>¡Cuenta conectada!</h2><p>{msg}</p>{return_btn}</body></html>",
                        )
                        on_login_success()
                        return

                # Caso 3: Supabase devolvió los tokens en el fragmento #access_token=...
                bridge_html = """<!DOCTYPE html>
                <html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head>
                <body style="font-family:sans-serif;text-align:center;padding:60px 20px;background:#0f172a;color:#fff;">
                <p>Procesando autenticación con Google...</p>
                <script>
                if (window.location.hash && window.location.hash.length > 1) {
                    window.location.replace("/callback?" + window.location.hash.substring(1));
                } else {
                    document.body.innerHTML = "<h3>No se recibió código de autorización. Vuelve a intentarlo desde la app.</h3>";
                }
                </script></body></html>"""
                self._send_html(200, bridge_html)

        def run_server():
            try:
                server = ReusableHTTPServer(("127.0.0.1", LOOPBACK_PORT), OAuthCallbackHandler)
                server.timeout = 2.0
                service._active_oauth_server = server
                deadline = time.time() + 180  # 3 minutos para completar login
                while not auth_completed.is_set() and time.time() < deadline:
                    server.handle_request()
                server.server_close()
            except Exception:
                pass
            finally:
                service._active_oauth_server = None

        threading.Thread(target=run_server, daemon=True).start()

    # --- Sincronización Bidireccional Offline-First con Supabase PostgREST ---
    def sync_pending_transactions(self) -> tuple[bool, int, str]:
        """Ejecuta borrados pendientes, sube creaciones/ediciones y unifica con Supabase sin duplicar."""
        if not self.is_configured:
            return False, 0, "Faltan credenciales de Supabase en settings.py"
        if not self.user_id:
            return False, 0, "Inicia sesión para respaldar tus datos en la nube"

        if not self._sync_lock.acquire(blocking=False):
            return False, 0, "Sincronización en curso..."

        try:
            if not self._ensure_valid_session():
                return False, 0, "Sesión expirada. Vuelve a iniciar sesión."

            # 1. Procesar cola de eliminaciones pendientes (evita Gastos Zombie)
            pending_deletes = self.local_storage.get_pending_deletes()
            deleted_ids = []
            for del_id in pending_deletes:
                q_id = urllib.parse.quote(str(del_id), safe="")
                q_uid = urllib.parse.quote(str(self.user_id), safe="")
                status, _ = self._request(
                    "DELETE",
                    f"/rest/v1/transactions?id=eq.{q_id}&user_id=eq.{q_uid}",
                )
                if status in (200, 204):
                    deleted_ids.append(del_id)
            if deleted_ids:
                self.local_storage.clear_from_delete_queue(deleted_ids)

            # 2. Procesar cola de subidas y ediciones pendientes
            pending_upserts = self.local_storage.get_pending_queue()
            synced_ids = []
            for tx in pending_upserts:
                payload = {
                    "id": tx["id"],
                    "user_id": self.user_id,
                    "type": tx["type"],
                    "amount": float(tx["amount"]),
                    "category": tx["category"],
                    "note": tx.get("note", ""),
                    "created_at": tx["created_at"],
                }
                status, res_data = self._request(
                    "POST",
                    "/rest/v1/transactions?on_conflict=id",
                    body=payload,
                    extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
                )
                if status in (200, 201, 204):
                    synced_ids.append(tx["id"])
                else:
                    err_msg = self._extract_error_message(res_data, f"HTTP {status}")
                    return False, len(synced_ids), f"Error al subir a Supabase: {err_msg}"

            if synced_ids:
                self.local_storage.clear_from_queue(synced_ids)

            # 3. Descargar estado remoto y unificar por diccionario único (ID)
            q_uid = urllib.parse.quote(str(self.user_id), safe="")
            status, remote_data = self._request(
                "GET",
                f"/rest/v1/transactions?select=*&user_id=eq.{q_uid}&order=created_at.desc",
            )

            if status == 200 and isinstance(remote_data, list):
                remaining_deletes = set(self.local_storage.get_pending_deletes())
                unified_by_id: dict[str, dict] = {}

                for r_tx in remote_data:
                    if r_tx["id"] not in remaining_deletes:
                        r_tx["amount"] = float(r_tx["amount"])
                        r_tx["synced"] = True
                        unified_by_id[r_tx["id"]] = r_tx

                # Cualquier cambio local que aún no haya subido tiene prioridad sobre el remoto
                for local_pending in self.local_storage.get_pending_queue():
                    unified_by_id[local_pending["id"]] = local_pending

                merged_list = sorted(
                    unified_by_id.values(),
                    key=lambda x: str(x.get("created_at", "")),
                    reverse=True,
                )
                self.local_storage.save_transactions(merged_list)
                return True, len(synced_ids), f"Nube sincronizada ({len(merged_list)} movimientos)"

            err_detail = self._extract_error_message(remote_data, f"HTTP {status}")
            return False, len(synced_ids), f"No se pudo descargar historial: {err_detail}"
        except Exception as e:
            return False, 0, f"Modo Offline activo ({e})"
        finally:
            self._sync_lock.release()