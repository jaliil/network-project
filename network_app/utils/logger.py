import logging
import os
from datetime import datetime

# پوشه‌ی لاگ‌ها
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# نام فایل لاگ بر اساس تاریخ و زمان اجرا
log_filename = datetime.now().strftime("app_%Y-%m-%d_%H-%M-%S.log")
log_path = os.path.join(LOG_DIR, log_filename)

# تنظیمات لاگ فقط برای فایل
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# گرفتن logger آماده
logger = logging.getLogger("network_app")
