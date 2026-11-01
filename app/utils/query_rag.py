from app.utils import embeddings
import psycopg
from app.configs import settings


def query_rag(question: str, top_k: int = 3):
    question_embedding = embeddings.embed_query(question)

    conn = psycopg.connect(settings.database_url)

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT content
                FROM recomendation_team
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
                """,
                (question_embedding, top_k),
            )

            rows = cursor.fetchall()

    finally:
        conn.close()

    context = "\n\n".join(row[0] for row in rows)

    return context
