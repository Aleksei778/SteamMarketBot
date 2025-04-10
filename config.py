from dotenv import load_dotenv
import os

load_dotenv()

# Фильтры
PRICE_MIN = float(os.getenv("PRICE_MIN")) # минимальная цена USD
PRICE_MAX = float(os.getenv("PRICE_MAX")) # максимальная цена USD
OVERPAY_THRESHOLD_GOOD = os.getenv("OVERPAY_THRESHOLD_GOOD") # нормальная переплата
OVERPAY_THRESHOLD_BAD = os.getenv("OVERPAY_THRESHOLD_BAD") # ненормальная переплата

# Пароль и логин от стима
STEAM_LOGIN = os.getenv("STEAM_LOGIN") # логин стима
STEAM_PASSWORD = os.getenv("STEAM_PASSWORD") # пароль стима
STEAM_API_KEY = os.getenv("STEAM_API_KEY") # ключ API Steam
STEAM_LOGIN_SECURE = os.getenv("STEAM_LOGIN_SECURE")

# Базовый URL для площадки стим
BASE_URL = os.getenv("BASE_URL")