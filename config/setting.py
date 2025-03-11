import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

class AppSettings(BaseSettings):
    API_NAME: str = "Voucher-Purchase-System"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "Voucher Purchase System"
    API_PREFIX: str = "/api/v1"
    DATABASE_URL: str = DATABASE_URL

    class config:
        env_file = ".env"


app_settings = AppSettings()
