import os
import flet as ft
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://gwfbmplmszezjunpvllz.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_Mmd4WFqPDyzeT5wW-ww2Sg_ICMOLOR4")
CURRENCY_SYMBOL = "S/"
THEME_SEED_COLOR = "#10B981"  # Verde esmeralda financiero
MAX_TRANSACTION_AMOUNT = 9999999.99

# Categorías de Gastos
EXPENSE_CATEGORIES = {
    "Alimentación": {"icon": ft.Icons.RESTAURANT, "color": ft.Colors.ORANGE_400, "group": "Necesidades (50%)"},
    "Vivienda y Servicios": {"icon": ft.Icons.HOME, "color": ft.Colors.BLUE_400, "group": "Necesidades (50%)"},
    "Transporte": {"icon": ft.Icons.DIRECTIONS_CAR, "color": ft.Colors.CYAN_400, "group": "Necesidades (50%)"},
    "Ocio y Salidas": {"icon": ft.Icons.LOCAL_CAFE, "color": ft.Colors.PURPLE_400, "group": "Deseos (30%)"},
    "Compras Personales": {"icon": ft.Icons.SHOPPING_BAG, "color": ft.Colors.PINK_400, "group": "Deseos (30%)"},
    "Ahorro e Inversión": {"icon": ft.Icons.SAVINGS, "color": ft.Colors.GREEN_400, "group": "Futuro (20%)"},
}

# Categorías de Ingresos corregidas
INCOME_CATEGORIES = {
    "Sueldo / Honorarios": {"icon": ft.Icons.ACCOUNT_BALANCE_WALLET, "color": ft.Colors.TEAL_400},
    "Negocio / Ventas": {"icon": ft.Icons.STOREFRONT, "color": ft.Colors.GREEN_ACCENT_700},
    "Otros Ingresos": {"icon": ft.Icons.ADD_CARD, "color": ft.Colors.LIGHT_GREEN_400},
}

def delete_transaction_local(self, tx_id: str):
        # 1. Eliminar de la caché visual
        transactions = self.get_transactions()
        transactions = [tx for tx in transactions if tx["id"] != tx_id]

        # 2. Eliminar de la cola pendiente si aún no ha subido a Supabase
        queue = self.get_pending_queue()
        queue = [tx for tx in queue if tx["id"] != tx_id]
        self.page.client_storage.set(self.PENDING_QUEUE_KEY, json.dumps(queue))