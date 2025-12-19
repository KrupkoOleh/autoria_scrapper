import os

from dotenv import load_dotenv
from pydantic.v1 import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    DB_HOST: str = os.getenv('DB_HOST')
    DB_PORT: int = os.getenv('DB_PORT')
    DB_USER: str = os.getenv('DB_USER')
    DB_PASS: str = os.getenv('DB_PASS')
    DB_NAME: str = os.getenv('DB_NAME')

    @property
    def DATABASE_URL_asyncpg(self):
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"  # noqa


settings = Settings()
