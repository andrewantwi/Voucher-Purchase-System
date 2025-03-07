from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from config.setting import app_settings


class DatabaseSetup:
    def __init__(self) -> None:
        self._engine = create_engine(app_settings.DATABASE_URL)
        self._session_maker = sessionmaker(
            autocommit=False, autoflush=False, bind=self._engine)
        self._base = declarative_base()

    def get_base(self):
        return self._base

    def get_session(self) -> sessionmaker:
        return self._session_maker

    def get_engine(self):
        return self._engine


database = DatabaseSetup()
Base = database.get_base()
