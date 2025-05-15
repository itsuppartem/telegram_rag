import os
import logging
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set!")

ADMIN_IDS_STR = os.getenv('TELEGRAM_ADMIN_IDS', '')
ADMIN_IDS = set()

if ADMIN_IDS_STR:
    try:
        admin_ids_list = []
        raw_ids = ADMIN_IDS_STR.split(',')
        for id_str in raw_ids:
            id_part = id_str.split('#', 1)[0]
            cleaned_id = id_part.strip()
            if cleaned_id:
                admin_ids_list.append(cleaned_id)
        ADMIN_IDS = {int(admin_id) for admin_id in admin_ids_list}
        logging.info(f"Успешно загружены ID администраторов: {ADMIN_IDS}")
    except ValueError as e:
        logging.error(f"Ошибка при парсинге TELEGRAM_ADMIN_IDS: {e}")
        logging.error(f"Проверьте значение TELEGRAM_ADMIN_IDS: '{ADMIN_IDS_STR}'")
        raise ValueError("Некорректный формат TELEGRAM_ADMIN_IDS")

FASTAPI_BASE_URL = os.getenv('FASTAPI_BASE_URL', 'http://localhost:8000')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) 