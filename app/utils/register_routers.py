from fastapi import FastAPI
from app.routes import recomendation_team_router
from app.routes import chat_router


def register_routers(app: FastAPI):
    app.include_router(recomendation_team_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")
