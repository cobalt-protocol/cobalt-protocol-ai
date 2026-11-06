from app.utils.ai import CompetitionChat
from fastapi.responses import JSONResponse


class ChatControllers:
    @staticmethod
    async def chat(current_user, competition_id, question):
        result = await CompetitionChat.tanya_competition(
            question, competition_id, current_user["data"]["user"]["id"]
        )
        return JSONResponse(
            content={
                "data": {"answer": result},
                "message": "answer is found",
                "errors": None,
            },
            status_code=201,
        )
