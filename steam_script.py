import httpx
from bs4 import BeautifulSoup
from steam.client import SteamClient
from steam.guard import SteamAuthenticator
from steam.enums import EResult
import logging
import asyncio
from urllib.parse import quote
import re
import sys

from config import (
    PRICE_MAX,
    PRICE_MIN,
    OVERPAY_THRESHOLD_GOOD,
    OVERPAY_THRESHOLD_BAD,
    STEAM_PASSWORD,
    STEAM_LOGIN,
    BASE_URL
)

class SteamMarketBot:
    def __init__(self):
        self.setup_logging()
        # self.login_to_steam()
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://steamcommunity.com/market/"
            }
        )

    def setup_logging(self):
        formatter = logging.Formatter('%(asctime)s - %(message)s')

        file_handler = logging.FileHandler("steam_market_bot.log", encoding='UTF-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        logging.basicConfig(
            level=logging.INFO,
            handlers=[
                file_handler,
                console_handler
            ]
        )

    def build_url_for_items(self, stickers = None, order_of_stickers = False, weapon = None, exteriors=None, quality=None, sort_by_price='asc'):
        """
        Функция создания URL, которое генерируется 
        csgostickersearch при выставлении параметров

        Args:
            stickers (list): Список стикеров
            order_of_stickers(bool): Порядок стикеров
            weapon (str): Тип оружия (например, "bizon", "awp", "ak47")
            exteriors (list): Состояние скина (от 0 до 4)
            quality (str): Качество предмета (например, "strange")
            sort_by_price (str): Сортировать по цене ('desc', 'asc')
        
        Returns:
            str: URL для поиска на Steam Market
        """

        params = {}

        stickers_str = ""
        if stickers:
            if order_of_stickers:
                stickers_str = ",".join(stickers)
                encoded_stickers_str = f'"{quote(stickers_str, safe=',')}"'
            else:
                encoded_stickers_str = " + ".join([f'"{quote(sticker)}"' for sticker in stickers])
        else:
            encoded_stickers_str = '""'

        params['q'] = encoded_stickers_str
        params['descriptions'] = 1
        params[quote('category_730_ItemSet[]')] = 'any'
        
        if exteriors is not None:
            params[quote('category_730_Exterior[]')] = "&".join([f"tag_WearCategory{exterior}" for exterior in exteriors])

        params[quote('category_730_Weapon[]')] = 'any' if weapon is None else f'tag_weapon_{weapon}'
        params[quote('category_730_Quality[]')] = '' if quality is None else f'tag_{quality}'

        url = f"{BASE_URL}?"
        for key, value in params.items():
            url += f"{key}={value}&"
        url = url[:-1]
        url += f"#p1_price_{sort_by_price}"

        return url



    def login_to_steam(self):
        self.steam_client = SteamClient()
        self.authentificator = SteamAuthenticator(self.steam_client)

        logging.info(f"Вход в Steam как {STEAM_LOGIN}")
        result = self.steam_client.login(username=STEAM_LOGIN, password=STEAM_PASSWORD)

        if result == EResult.OK:
            logging.info(f"Успешный вход")
            self.session_id = self.steam_client.session_id
            self.http_client.cookies.update({"sessionid": self.session_id})
            self.http_client.cookies.update({"steamLoginSecure": self.steam_client.steam_login_secure})
        else:
            logging.error(f"Ошибка входа")
            raise Exception("Не удалось войти в Steam")

    async def search_for_items(self, monitored_items: dict):
        url = self.build_url_for_items(**monitored_items)

        response = await self.http_client.get(url)
        if (response.status_code != 200):
            logging.error(f"Ошибка запроса: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        listings = soup.find_all("a", class_='market_listing_row_link')

        items = []

        for listing in listings:
            try:
                name_element = listing.find("span", class_='market_listing_item_name')
                item_name = name_element.text.strip()

                price_element = listing.find("span", class_='market_listing_item_price')
                price_text = price_element.text.strip()
                price = self.extract_price(price_text=price_text)

                listing_id_match = re.search(r'mylisting_(\d+)', listing.get('id', ''))
                listing_id = listing_id_match.group(1) if listing_id_match else None
                
                item_url = listing.get("href")

                item_data = {
                    'name': item_name,
                    'price': price,
                    'listing_id': listing_id,
                    'item_url': item_url
                }

                if PRICE_MIN <= price and price <= PRICE_MAX:
                    items.append(item_data)

            except Exception as e:
                logging.error(f"Не вышло получить информацию о предмете: {str(e)}")
                continue

        logging.info(f"Было получено {len(items)} предметов.")
        return items

    def extract_price(self, price_text):
        """Extract numerical price from string"""
        # Remove currency symbols and non-numeric characters except for decimal point
        numeric_chars = re.sub(r'[^\d.,]', '', price_text)
        # Replace comma with dot for decimal point if needed
        numeric_chars = numeric_chars.replace(',', '.')
        try:
            return float(numeric_chars)
        except ValueError:
            return 0.0

    async def check_overpay(self):
        pass

    async def buy_item(self, item):
        try:
            listing_id = item['listing_id']
            url = "https://steamcommunity.com/market/buylisting"
            
            payload = {
                'sessionid': self.session_id,
                'listingid': listing_id,
                'quantity': 1,
                'fee': 0,
                'subtotal': 0
            }

            logging.info(f"Попытка покупки предмета: {item}")
            response = await self.http_client.post(url, data=payload)

            if response.status_code == 200:
                data = response.json()
                if data.get('success') == 1:
                    logging.info(f"Покупка прошла успешно")
                    return True
                else:
                    error = data.get('message', 'Неизвестная ошибка')
                    logging.error(f"Purchase failed: {error}")
            else:
                logging.error(f"Статус ошибки: {response.status_code}")

        except Exception as e:
            logging.error(f"Ошибка в процессе покупки: {str(e)}")

        return False
    
    async def monitor_market(self, search_params, interval_sec = 60):
        while True:
            try:
                items = await self.search_for_items(search_params)

                for item in items:
                    success = await self.buy_item(item)
                    
                    if success:
                        logging.info(f"Успешная покупка предмета: {item}")
                    else:
                        logging.warning(f"Не получилось купить предмет: {item}")
                    
                await asyncio.sleep(interval_sec)
            
            except Exception as e:
                logging.error(f"Какие-то проблемы с мониторингом рынка: {str(e)}")
                await asyncio.sleep(interval_sec)




async def main():
    steam_market_bot = SteamMarketBot()
    
    search_params = {
        'stickers': ["Natus Vincere Paris 2023"],
        'weapon': 'ak-47',
        'order_of_stickers': False,
        'exteriors': [2, 4],
        'quality': None,
        'sort_by_price': 'asc'
    }
    
    print(steam_market_bot.build_url_for_items(**search_params))


    # await steam_market_bot.monitor_market(search_params, interval_sec=120)

if __name__ == "__main__":
    asyncio.run(main())