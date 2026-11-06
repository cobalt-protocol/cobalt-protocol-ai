from fastapi import APIRouter, Depends, status
from app.utils.middlewares import verify_auth_token
from app.controllers import ChatControllers
from app.schemas.chat import ChatRequest

chat_router = APIRouter()
chat_controllers = ChatControllers()


@chat_router.post(
    "/chat/{competition_id}",
    status_code=status.HTTP_200_OK,
)
async def chat(
    competition_id: str,
    request: ChatRequest,
    current_user: str = Depends(verify_auth_token),
):
    return await ChatControllers.chat(current_user, competition_id, request.question)
