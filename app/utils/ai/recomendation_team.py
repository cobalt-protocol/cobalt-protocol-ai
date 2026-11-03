from app.configs import settings
import requests
import psycopg
from app.utils.langchain_embed import embeddings
from app.utils.ai.model_balancer import ModelBalancer


class RecomendationTeam:
    @staticmethod
    async def query_rag(question: str, top_k: int = 3):
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

    @staticmethod
    async def recomendation_team(question: str):
        context = await RecomendationTeam.query_rag(question)

        prompt = """
Jawab pertanyaan berdasarkan konteks berikut.

Kamu Di Tugaskan untuk memberikan list rekomendasi team terbaik berdasarkan konteks.

Aturan:
- Kembalikan dalam bentuk tipe data array yang di dalamnya ada key dan value yang valid, untuk keynya hanya ada team_id
- Output Jangan di bungkus pakai apapun itu, pastikan outputnya bersih
- Berikut contoh output data yang tepat : [{'team_id':'01M5Y32MGGJYQ56XP29D7QRW7N'}].
- Setiap team_id harus berupa string.
- Jangan menambahkan spasi di awal atau akhir team_id.
- Jangan menambahkan penjelasan di luar array.
- Jika tidak ditemukan, kembalikan [].
- Jika dia bertanya untuk spesifik team butuh orang seperti apa, kembalikan []

Konteks:
{context}

Pertanyaan:
{question}
""".replace("{context}", context).replace("{question}", question)

        model_id = await ModelBalancer.find_first_healthy_model()

        data = {
            "model": model_id,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "stream": False,
            "max_tokens": 1024,
            "temperature": 0.7,
        }

        response = requests.post(
            f"https://llm.chutes.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.api_key_chutes}",
                "Content-Type": "application/json",
            },
            json=data,
            timeout=120,
        )

        response.raise_for_status()

        result = response.json()

        return result["choices"][0]["message"]["content"]
