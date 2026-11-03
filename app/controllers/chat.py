from app.utils.ai import CompetitionChat
import psycopg
from app.configs import settings
from psycopg.rows import dict_row
from fastapi.responses import JSONResponse


class ChatControllers:
    @staticmethod
    async def chat(competition_id, question):
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """SELECT *
                        FROM competition
                        WHERE id = %s
                            AND deleted_at IS NULL;
                    """,
                    (competition_id,),
                )

                row = cursor.fetchone()
                result = await CompetitionChat.result_chat(
                    question,
                    competition_id,
                    f'http://localhost:8081/ipfs/{row["guidebook_cid"]}',
                )
                return JSONResponse(
                    content={
                        "data": {"answer": result},
                        "message": "answer is found",
                        "errors": None,
                    },
                    status_code=201,
                )
