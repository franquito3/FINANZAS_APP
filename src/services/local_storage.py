import json
import uuid
from datetime import datetime
import flet as ft

class LocalStorageService:
    TRANSACTIONS_KEY = "finanzas_transactions_cache"
    PENDING_QUEUE_KEY = "finanzas_pending_sync_queue"
    PENDING_DELETE_KEY = "finanzas_pending_delete_queue"
    SESSION_KEY = "finanzas_jwt_session"

    def __init__(self, page: ft.Page):
        self.page = page

    # --- Gestión de Sesión ---
    def save_session(self, session_data: dict):
        self.page.client_storage.set(self.SESSION_KEY, json.dumps(session_data))

    def get_session(self) -> dict | None:
        raw = self.page.client_storage.get(self.SESSION_KEY)
        return json.loads(raw) if raw else None

    def clear_session(self):
        self.page.client_storage.remove(self.SESSION_KEY)

    # --- Gestión de Transacciones ---
    def get_transactions(self) -> list[dict]:
        raw = self.page.client_storage.get(self.TRANSACTIONS_KEY)
        return json.loads(raw) if raw else []

    def save_transactions(self, transactions: list[dict]):
        self.page.client_storage.set(self.TRANSACTIONS_KEY, json.dumps(transactions))

    def add_transaction_local(
        self,
        tx_type: str,
        amount: float,
        category: str,
        note: str,
        user_id: str = "local_user",
        created_at: str | None = None,
    ) -> dict:
        tx_date = created_at or datetime.now().isoformat()
        new_tx = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "type": tx_type,
            "amount": round(float(amount), 2),
            "category": category,
            "note": note,
            "created_at": tx_date,
            "synced": False,
        }
        transactions = self.get_transactions()
        transactions.insert(0, new_tx)
        transactions.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
        self.save_transactions(transactions)

        queue = [q for q in self.get_pending_queue() if q["id"] != new_tx["id"]]
        queue.append(new_tx)
        self.page.client_storage.set(self.PENDING_QUEUE_KEY, json.dumps(queue))
        return new_tx

    def update_transaction_local(
        self,
        tx_id: str,
        tx_type: str,
        amount: float,
        category: str,
        note: str,
        created_at: str | None = None,
    ):
        transactions = self.get_transactions()
        updated_tx = None

        for tx in transactions:
            if tx["id"] == tx_id:
                tx["type"] = tx_type
                tx["amount"] = round(float(amount), 2)
                tx["category"] = category
                tx["note"] = note
                if created_at:
                    tx["created_at"] = created_at
                tx["synced"] = False
                updated_tx = tx
                break

        transactions.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
        self.save_transactions(transactions)

        if updated_tx:
            queue = [q for q in self.get_pending_queue() if q["id"] != tx_id]
            queue.append(updated_tx)
            self.page.client_storage.set(self.PENDING_QUEUE_KEY, json.dumps(queue))

    def delete_transaction_local(self, tx_id: str):
        transactions = self.get_transactions()
        target_tx = next((tx for tx in transactions if tx["id"] == tx_id), None)

        # 1. Quitar de la caché visual
        transactions = [tx for tx in transactions if tx["id"] != tx_id]
        self.save_transactions(transactions)

        # 2. Quitar de la cola de subida pendiente
        queue = [tx for tx in self.get_pending_queue() if tx["id"] != tx_id]
        self.page.client_storage.set(self.PENDING_QUEUE_KEY, json.dumps(queue))

        # 3. Si ya estaba en Supabase (o por seguridad), encolar para borrado remoto cuando haya internet
        if target_tx is None or target_tx.get("synced", False):
            del_queue = self.get_pending_deletes()
            if tx_id not in del_queue:
                del_queue.append(tx_id)
                self.page.client_storage.set(self.PENDING_DELETE_KEY, json.dumps(del_queue))

    # --- Colas de Sincronización ---
    def get_pending_queue(self) -> list[dict]:
        raw = self.page.client_storage.get(self.PENDING_QUEUE_KEY)
        return json.loads(raw) if raw else []

    def get_pending_deletes(self) -> list[str]:
        raw = self.page.client_storage.get(self.PENDING_DELETE_KEY)
        return json.loads(raw) if raw else []

    def clear_from_delete_queue(self, deleted_ids: list[str]):
        del_queue = [tx_id for tx_id in self.get_pending_deletes() if tx_id not in deleted_ids]
        self.page.client_storage.set(self.PENDING_DELETE_KEY, json.dumps(del_queue))

    def clear_from_queue(self, synced_ids: list[str]):
        queue = [tx for tx in self.get_pending_queue() if tx["id"] not in synced_ids]
        self.page.client_storage.set(self.PENDING_QUEUE_KEY, json.dumps(queue))

        transactions = self.get_transactions()
        for tx in transactions:
            if tx["id"] in synced_ids:
                tx["synced"] = True
        self.save_transactions(transactions)