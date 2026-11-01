from fastapi import FastAPI
from app.routes import recomendation_team


def register_routers(app: FastAPI):
    app.include_router(recomendation_team.router, prefix="/api")
