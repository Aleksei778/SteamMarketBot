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
    BASE_URL,
    STEAM_LOGIN_SECURE
)

class SteamMarketBot:
    def __init__(self):
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": "https://steamcommunity.com/market/"
            }
        )

        self.setup_logging()

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

    

    def build_url_for_items(self, start=0, count=3, stickers=None, order_of_stickers=False, weapon=None, exteriors=None, quality=None, sort_by_price='asc'):
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
                encoded_stickers_str = " ".join([f'"{quote(sticker)}"' for sticker in stickers])
        else:
            encoded_stickers_str = '""'

        params['start'] = str(start)  # Преобразуем в строку
        params['count'] = str(count)  # Преобразуем в строку
        params['q'] = encoded_stickers_str
        params['descriptions'] = '1'  # Преобразуем в строку
        params[quote('category_730_ItemSet[]')] = 'any'
        
        if exteriors is not None:
            exterior_params = []
            for exterior in exteriors:
                exterior_params.append(f"tag_WearCategory{exterior}")
            params[quote('category_730_Exterior[]')] = "&".join(exterior_params)

        params[quote('category_730_Weapon[]')] = 'any' if weapon is None else f'tag_weapon_{weapon}'
        params[quote('category_730_Quality[]')] = '' if quality is None else f'tag_{quality}'

        url = f"{BASE_URL}/render?"
        for key, value in params.items():
            url += f"{key}={value}&"
        url = url[:-1]  # Удаляем последний символ &
        url += f"&sort_column=price&sort_dir={sort_by_price}"
    
        return url

    async def login_to_steam(self):
        self.steam_client = SteamClient()
        self.authenticator = SteamAuthenticator(self.steam_client)

        logging.info(f"Вход в Steam как {STEAM_LOGIN}")
        result = self.steam_client.login(username=STEAM_LOGIN, password=STEAM_PASSWORD)

        if result == EResult.OK:
            logging.info(f"Успешный вход")
            self.session_id = str(self.steam_client.session_id)
            self.http_client.cookies.update({
                "sessionid": self.session_id,
                # "steamLoginSecure": STEAM_LOGIN_SECURE,
                "steamCurrencyId": "5"
            })
        elif result == EResult.AccountLoginDeniedNeedTwoFactor:
            logging.info("Требуется код двухфакторной аутентификации")
            code = input("Введите код Steam Guard из мобильного приложения: ")
            
            # Убедимся, что код - строка, а не число
            code = str(code).strip()
            
            # Проверим, что код был введен
            if not code:
                logging.warning("Код не был введен, попытка входа без кода")
                
            # Добавим отладочную информацию
            logging.info(f"Тип кода: {type(code)}, значение: {code}")
            
            # Попробуем войти с кодом
            result = self.steam_client.login(username=STEAM_LOGIN, password=STEAM_PASSWORD, two_factor_code=code)

            if result == EResult.OK:
                logging.info(f"Успешный вход")
                self.session_id = str(self.steam_client.session_id)
                response = await self.http_client.get("https://steamcommunity.com/my", follow_redirects=True, cookies={"sessionid": self.session_id})
                steam_login_secure = response.cookies.get("steamLoginSecure")
                if steam_login_secure:
                    logging.info(f"Получен steamLoginSecure: {steam_login_secure.value}")
                else:
                    logging.warning("steamLoginSecure не найден в ответе")
                
                self.http_client.cookies.update({
                    "sessionid": self.session_id,
                    "steamLoginSecure": steam_login_secure if steam_login_secure else "",
                    "steamCurrencyId": "5"
                })
                '''
                    self.session_id = str(self.steam_client.session_id)
                self.http_client.cookies.update({
                    "sessionid": self.session_id,
                    # "steamLoginSecure": STEAM_LOGIN_SECURE,
                    "steamCurrencyId": "5"
                })
                '''
            else:
                logging.error(f"Ошибка входа после ввода кода: {result}")
                raise Exception("Не удалось войти в Steam после ввода кода")
        else:
            print(result)
            logging.error(f"Ошибка входа: {result}")
            raise Exception("Не удалось войти в Steam")
    
    async def search_for_items(self, monitored_items: dict):
        url = self.build_url_for_items(**monitored_items)
        logging.info(f"Generated URL: {url}")

        if not isinstance(url, str):
            logging.error(f"URL должен быть строкой, получено: {type(url)} - {url}")
            return []

        response = await self.http_client.get(url=str(url))  # Используем get напрямую

        if response.status_code != 200:
            logging.error(f"Ошибка запроса: {response.status_code}")
            return []
        print("Нет ошибки2")
        
        soup = BeautifulSoup(response.json()['results_html'], 'html.parser')
        listings = soup.find_all("a", class_='market_listing_row_link')

        items = []

        for listing in listings:
            try:
                name_element = listing.find("span", class_='market_listing_item_name')
                item_name = name_element.text.strip()
                print(name_element, item_name)

                price_element = listing.find("span", class_='normal_price')
                price_element2 = price_element.find("span", class_='normal_price')
                print(price_element2)
                price_text = price_element2.text.strip()
                price = self.extract_price(price_text=price_text)
                print(f"Цена элемента: {price_element}, цена текст: {price_text}, цена: {price}")
                
                item_url = listing.get("href")

                listing_id = await self.get_listing_id_from_url(item_url)
                if not listing_id:
                    logging.warning(f"Не удалось найти listing_id для {item_name}")
                    continue

                item_data = {
                    'name': item_name,
                    'price': price,
                    'listing_id': listing_id,
                    'item_url': item_url
                }

                if PRICE_MIN <= price and price <= PRICE_MAX:
                    items.append(item_data)
                else:
                    print(f"ЦЕна вопроса {price}, макс {PRICE_MAX}, мин {PRICE_MIN}")

            except Exception as e:
                logging.error(f"Не вышло получить информацию о предмете: {str(e)}")
                continue

        logging.info(f"Было получено {len(items)} предметов.")
        
        return items

    async def get_listing_id_from_url(self, item_url):
        request = self.http_client.build_request("GET", item_url)
        response = await self.http_client.send(request=request)

        if response.status_code != 200:
            logging.error(f"Не удалось отправить запрос для получения listing_id по url: {item_url}")

            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        listing_row = soup.find("div", class_='market_listing_row', id=re.compile(r'listing_\d+'))
        if listing_row:
            listing_id = listing_row.get("id").replace("listing_", "")
            logging.info(f"Найден listing_id: {listing_id} для URL: {item_url}")
            return listing_id
        logging.warning(f"Не найдено listing_id на странице: {item_url}")
        return None

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
            url = f"https://steamcommunity.com/market/buylisting/{listing_id}"
            price = item['price']  # Цена в рублях (например, 0.03)
            subtotal = int(price * 100)  # Цена в копейках без комиссии
            # Примерная комиссия Steam: 13% (можно уточнить)
            fee = int(subtotal * 0.13)  # Комиссия в копейках
            total = subtotal + fee  # Итоговая цена с комиссией

            '''
            payload = {
                'sessionid': str(self.session_id),  # Убедимся, что строка
                'quantity': '1',                   # Строковое значение
                'subtotal': str(subtotal),         # Строковое значение
                'fee': str(fee),                   # Строковое значение
                'total': str(total),               # Строковое значение
                'currencyid': '5'                  # RUB
            }

            print(payload)

            headers = {
                'Referer': item['item_url'],       # Ссылка на страницу листинга
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Origin': 'https://steamcommunity.com',
                "User-Agent": "Mozilla/5.0"
            }
            '''
            form = {
                "sessionid": self.session_id,  # строка, полученная при входе
                "currency": "5",          # ID валюты (5 = рубли)
                "subtotal": str(price),   # цена без комиссии
                "fee": str(fee),          # комиссия
                "total": str(price + fee),  # цена с комиссией
                "quantity": "1"
            }

            headers = {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
            }

            response = await self.http_client.post(
                f"https://steamcommunity.com/market/buylisting/{listing_id}",
                headers=headers,
                data=form  # или data=URLSearchParams(form).toString() если хочешь вручную
            )

            logging.info(f"Попытка покупки предмета: {item}, payload: {form}")
            # response = await self.http_client.post(url, data=payload, headers=headers)



            if response.status_code == 200:
                data = response.json()
                if data.get('success') == 1:
                    logging.info(f"Покупка прошла успешно: {item['name']} за {price} RUB")
                    return True
                else:
                    error = data.get('message', 'Неизвестная ошибка')
                    logging.error(f"Purchase failed: {error}")
            else:
                logging.error(f"Статус ошибки: {response.status_code}")
                logging.error(f"Ответ сервера: {response.text}")

        except Exception as e:
            logging.error(f"Ошибка в процессе покупки: {str(e)}")
        return False
    


    async def monitor_market(self, search_params, interval_sec = 60):
        while True:
            items = await self.search_for_items(search_params)

            for item in items:
                success = await self.buy_item(item)
                
                if success:
                    logging.info(f"Успешная покупка предмета: {item}")
                else:
                    logging.warning(f"Не получилось купить предмет: {item}")
                
            await asyncio.sleep(interval_sec)




async def main():
    steam_market_bot = SteamMarketBot()
    await steam_market_bot.login_to_steam()
    search_params = {
        'stickers': ["Natus Vincere Paris 2023"],
        # 'weapon': 'ak-47',
        'order_of_stickers': False,
        'exteriors': [2, 4],
        'quality': None,
        'sort_by_price': 'asc'
    }
    
    # print(steam_market_bot.build_url_for_items(**search_params))


    await steam_market_bot.monitor_market(search_params, interval_sec=120)

if __name__ == "__main__":
    asyncio.run(main())