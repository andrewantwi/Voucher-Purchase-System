from fastapi import FastAPI, responses
from fastapi.middleware.cors import CORSMiddleware

from core import setup as db_setup
from api.v1.router import user, auth, voucher
from config.setting import app_settings


class AppBuilder:
    def __init__(self):
        self._app = FastAPI(title=app_settings.API_NAME,
                            description=app_settings.API_DESCRIPTION,redirect_slashes=False
                            )

    def register_routes(self):
        """ Register all routes """

        self._app.include_router(
            user.user_router,
            prefix=app_settings.API_PREFIX,
            tags=["User"])

        self._app.include_router(
            auth.auth_router,
            prefix=app_settings.API_PREFIX,
            tags=["Auth"])

        self._app.include_router(
            voucher.voucher_router,
            prefix=app_settings.API_PREFIX,
            tags=["Voucher"])

        @self._app.get("/", include_in_schema=False)
        def index():
            return responses.RedirectResponse(url="/docs")


    def register_database(self) -> None:
        db_setup.Base.metadata.create_all(bind=db_setup.database.get_engine())

    def register_middleware(self)-> None:
        self._app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def get_app(self):
        self.register_routes()
        self.register_database()
        self.register_middleware()
        return self._app
