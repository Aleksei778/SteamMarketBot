from dotenv import load_dotenv
import os

load_dotenv()

# Фильтры
PRICE_MIN = os.getenv("PRICE_MIN") # минимальная цена
PRICE_MAX = os.getenv("PRICE_MAX") # максимальная цена
OVERPAY_THRESHOLD_GOOD = os.getenv("OVERPAY_THRESHOLD_GOOD") # нормальная переплата
OVERPAY_THRESHOLD_BAD = os.getenv("OVERPAY_THRESHOLD_BAD") # ненормальная переплата

# Пароль и логин от стима
STEAM_LOGIN = os.getenv("STEAM_LOGIN") # логин стима
STEAM_PASSWORD = os.getenv("STEAM_PASSWORD") # пароль стима