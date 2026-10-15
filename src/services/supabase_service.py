import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from supabase import create_client, Client
from config.settings import SUPABASE_URL, SUPABASE_KEY
from services.local_storage import LocalStorageService

class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True

class SupabaseService:
    def __init__(self, local_storage: LocalStorageService):
        self.local_storage = local_storage
        self.client: Client | None = None
        self.user_id: str | None = None
        self.user_email: str | None = None
        self._sync_lock = threading.Lock()

        if SUPABASE_URL and SUPABASE_KEY and "tu-proyecto" not in SUPABASE_URL:
            try:
                self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
                self._restore_saved_session()
            except Exception:
                self.client = None

    def _restore_saved_session(self):
        saved = self.local_storage.get_session()
        if not saved or not self.client:
            return
        try:
            res = self.client.auth.set_session(saved["access_token"], saved["refresh_token"])
            if res and res.user and res.session:
                self.user_id = res.user.id
                self.user_email = res.user.email
                self.local_storage.save_session({
                    "access_token": res.session.access_token,
                    "refresh_token": res.session.refresh_token,
                    "user_id": res.user.id,
                    "email": res.user.email,
                })
        except Exception:
            # Si no hay internet al abrir la app, conservamos la identidad en caché
            self.user_id = saved.get("user_id")
            self.user_email = saved.get("email")

    def _ensure_valid_session(self):
        saved = self.local_storage.get_session()
        if not saved or not self.client:
            return
        try:
            res = self.client.auth.set_session(saved["access_token"], saved["refresh_token"])
            if res and res.session and res.user:
                self.user_id = res.user.id
                self.user_email = res.user.email
                self.local_storage.save_session({
                    "access_token": res.session.access_token,
                    "refresh_token": res.session.refresh_token,
                    "user_id": res.user.id,
                    "email": res.user.email,
                })
        except Exception:
            pass

    def logout(self):
        if self.client:
            try:
                self.client.auth.sign_out()
            except Exception:
                pass
        self.user_id = None
        self.user_email = None
        self.local_storage.clear_session()

    def start_google_login(self, on_login_success) -> str | None:
        if not self.client:
            return None
        try:
            response = self.client.auth.sign_in_with_oauth(
                {"provider": "google", "options": {"redirect_to": "http://localhost:8550"}}
            )
            self._listen_for_oauth_callback(on_login_success)
            return response.url
        except Exception:
            return None

    def _listen_for_oauth_callback(self, on_login_success):
        service = self

        class OAuthCallbackHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def do_GET(self):
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)

                if "code" in params:
                    auth_code = params["code"][0]
                    try:
                        res = service.client.auth.exchange_code_for_session({"auth_code": auth_code})
                        if res and res.user and res.session:
                            service.user_id = res.user.id
                            service.user_email = res.user.email
                            service.local_storage.save_session({
                                "access_token": res.session.access_token,
                                "refresh_token": res.session.refresh_token,
                                "user_id": res.user.id,
                                "email": res.user.email,
                            })
                            html = """
                            <html><body style="font-family:sans-serif;text-align:center;padding-top:80px;background:#121212;color:#fff;">
                            <h2 style="color:#10B981;">¡Cuenta de Google conectada con éxito!</h2>
                            <p>Ya puedes volver a tu aplicación Mis Finanzas.</p>
                            <script>setTimeout(function(){ window.close(); }, 1200);</script>
                            </body></html>
                            """
                            self.send_response(200)
                            self.send_header("Content-type", "text/html; charset=utf-8")
                            self.end_headers()
                            self.wfile.write(html.encode("utf-8"))

                            on_login_success()
                            return
                    except Exception as e:
                        error_msg = str(e)
                else:
                    error_msg = "No se recibió el código de autorización."

                self.send_response(400)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(f"<html><body><h3>Error de autenticación: {error_msg}</h3></body></html>".encode("utf-8"))

        def run_server():
            try:
                server = ReusableHTTPServer(("localhost", 8550), OAuthCallbackHandler)
                server.timeout = 180
                server.handle_request()
                server.server_close()
            except Exception:
                pass

        threading.Thread(target=run_server, daemon=True).start()

    def sync_pending_transactions(self) -> tuple[bool, int, str]:
        """Ejecuta borrados pendientes, sube creaciones/ediciones y unifica con Supabase sin duplicar."""
        if not self.client:
            return False, 0, "Faltan credenciales de Supabase en settings.py / .env"
        if not self.user_id:
            return False, 0, "Inicia sesión con Google para respaldar en la nube"

        if not self._sync_lock.acquire(blocking=False):
            return False, 0, "Sincronización en curso..."

        try:
            self._ensure_valid_session()

            # 1. Procesar cola de eliminaciones pendientes (evita Gastos Zombie)
            pending_deletes = self.local_storage.get_pending_deletes()
            deleted_ids = []
            for del_id in pending_deletes:
                self.client.table("transactions").delete().eq("id", del_id).eq("user_id", self.user_id).execute()
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
                    "amount": tx["amount"],
                    "category": tx["category"],
                    "note": tx.get("note", ""),
                    "created_at": tx["created_at"],
                }
                self.client.table("transactions").upsert(payload).execute()
                synced_ids.append(tx["id"])

            if synced_ids:
                self.local_storage.clear_from_queue(synced_ids)

            # 3. Descargar estado remoto y unificar por diccionario único (ID)
            remote_res = (
                self.client.table("transactions")
                .select("*")
                .eq("user_id", self.user_id)
                .order("created_at", desc=True)
                .execute()
            )

            if remote_res.data is not None:
                remaining_deletes = set(self.local_storage.get_pending_deletes())
                unified_by_id: dict[str, dict] = {}

                for r_tx in remote_res.data:
                    if r_tx["id"] not in remaining_deletes:
                        r_tx["amount"] = float(r_tx["amount"])
                        r_tx["synced"] = True
                        unified_by_id[r_tx["id"]] = r_tx

                # Cualquier cambio local que aún no haya subido tiene prioridad sobre el remoto
                for local_pending in self.local_storage.get_pending_queue():
                    unified_by_id[local_pending["id"]] = local_pending

                merged_list = sorted(
                    unified_by_id.values(),
                    key=lambda x: x.get("created_at", ""),
                    reverse=True,
                )
                self.local_storage.save_transactions(merged_list)

            return True, len(synced_ids), f"Nube actualizada ({len(synced_ids)} subidos)"
        except Exception as e:
            return False, 0, f"Modo Offline activo: {e}"
        finally:
            self._sync_lock.release()