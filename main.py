from fastapi import FastAPI
from app.configs import settings
from app.utils import register_routers, register_middlewares
import uvicorn

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug if settings.is_dev else False,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

register_middlewares(app)
register_routers(app)


@app.get("/")
async def read_root_endpoint():
    return {
        "message": "Welcome to the API!",
        "environment": settings.environment,
        "is_dev": settings.is_dev,
        "is_staging": settings.is_staging,
        "is_production": settings.is_production,
    }


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=True,
    )
