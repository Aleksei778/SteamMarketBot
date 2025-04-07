import httpx
from bs4 import BeautifulSoup
from steam.client import SteamClient
from steam.guard import SteamAuthenticator
from steam.enums import EResult
import logging
import asyncio

from config import (
    PRICE_MAX,
    PRICE_MIN,
    OVERPAY_THRESHOLD_GOOD,
    OVERPAY_THRESHOLD_BAD,
    STEAM_PASSWORD,
    STEAM_LOGIN
)

class SteamMarketBot:
    def __init__(self):
        self.setup_logging()
        self.login_to_steam()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            handlers=[
                logging.FileHandler("steam_market_bot.log"),
                logging.StreamHandler()
            ]
        )

    def login_to_steam(self):
        self.steam_client = SteamClient()
        self.authentificator = SteamAuthenticator()

        logging.info(f"Вход в Steam как {STEAM_LOGIN}")
        self.steam_client.login(username=STEAM_LOGIN, password=STEAM_PASSWORD)

        if self.steam_client.logged_on:
            logging.info("Успешный вход")
        else:
            logging.info("Ошибка входа")

    async def search_for_items(self):
        pass

    async def check_stickers(self):
        pass

    async def check_overpay(self):
        pass

    async def buy_item(self):
        pass
