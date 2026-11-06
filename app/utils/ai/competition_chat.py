import requests
import psycopg
from app.configs import settings
from app.utils.ai import ModelBalancer
from typing import Optional, Union
from datetime import datetime
import ulid
from redisvl.query.filter import Tag


class CompetitionChat:
    @staticmethod
    async def generate_ulid(
        timestamp: Optional[
            Union[int, float, str, bytes, bytearray, memoryview, datetime]
        ] = None,
    ) -> str:
        if timestamp is None:
            return str(ulid.ULID())

        return str(ulid.from_timestamp(timestamp))

    @staticmethod
    async def query_document_rag(question: str, top_k: int = 3):
        from app.utils.langchain_embed import embeddings

        question_embedding = embeddings.embed_query(question)

        query = """
            SELECT content
            FROM competition_guidebook_embedding
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
        """

        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (question_embedding, top_k))
                rows = cursor.fetchall()

        context = "\n\n".join(row[0] for row in rows)

        return context

    @staticmethod
    async def query_rag_question(question: str, top_k: int = 3):
        from app.utils.langchain_embed import embeddings

        question_embedding = embeddings.embed_query(question)

        query = """
            SELECT
                competition_id,
                chunk_type,
                content,
                1 - (embedding <=> %s::vector) AS similarity
            FROM competition_embedding
            WHERE deleted_at IS NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
        """

        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (question_embedding, question_embedding, top_k))

                rows = cursor.fetchall()

        context = "\n\n".join(f"""Competition ID: {row[0]}
Chunk Type: {row[1]}
Content: {row[2]}
Similarity: {row[3]:.4f}""" for row in rows)

        return context

    @staticmethod
    async def tanya_competition(question: str, competition_id: str, user_id):
        from app.configs.redis_config import vector_store

        prompt_template = """
Jawab pertanyaan berdasarkan konteks berikut.

Aturan:
- Untuk Konteks kompetisi/perlombaan/hackathonnya id nya adalah {competition_id}.
- Untuk jawaban terkait pertanyaan cek berdasarkan konteks perlombaan di bawah.
- Untuk konteks cek dahulu berdasarkan Konteks Memory, jika tidak yakin baru berdasarkan Konteks Perlombaan
- Jika tidak yakin dengan Konteks Perlombaan baru cek berdasarkan Konteks Guidebook
- Jika pertanyaan tidak sesuai konteks. outputnya saya tidak tahu.
- Tolong jawab pertanyaan sesuai kompetisi id : {competition_id}
- Jika user mention kompetisi id, dan tidak sama dengan {competition_id}. outputnya saya tidak tahu
- Pada output jangan menyebutkan kompetisi id
- Untuk output kirim dalam format markdown
- Untuk jawaban harus sesuai bahasa pertanyaa, misal pertanyaan pakai bahasa indonesia, berarti jawaban pakai bahasa indonesia.

Konteks Memory:
{context_memory}

Konteks Perlombaan:
{context}

Konteks Guidebook:
{guidebook}

Pertanyaan:
{question}
"""

        filter_expr = Tag("user_id") == user_id

        docs = vector_store.similarity_search(question, k=2, filter=filter_expr)
        context_memory = "\n\n".join(
            f"[Dokumen {i+1}] {doc.page_content}" for i, doc in enumerate(docs)
        )
        context = await CompetitionChat.query_rag_question(question)
        guidebook = await CompetitionChat.query_document_rag(question)

        prompt = (
            prompt_template.replace("{context}", context)
            .replace("{question}", question)
            .replace("{competition_id}", competition_id)
            .replace("{guidebook}", guidebook)
            .replace("{context_memory}", context_memory)
        )

        try:
            model_id = await ModelBalancer.find_first_healthy_model()
        except:
            print("error")

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
            f"{settings.base_url_chutes}chat/completions",
            headers={
                "Authorization": f"Bearer {settings.api_key_chutes}",
                "Content-Type": "application/json",
            },
            json=data,
            timeout=120,
        )

        response.raise_for_status()

        result = response.json()

        answer = result["choices"][0]["message"]["content"]

        texts = [f"""Pertanyaan:
{question}

Jawaban:
{answer}"""]
        metadatas = [
            {
                "source": f"doc_{await CompetitionChat.generate_ulid()}",
                "user_id": user_id,
            }
        ]

        ids_ = vector_store.add_texts(texts, metadatas=metadatas)

        query = """
                INSERT INTO history_chat (
                    id, 
                    id_redis, 
                    question, 
                    answer, 
                    user_id, 
                    created_at, 
                    updated_at
                ) VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    NOW(),
                    NOW()
                );
                """

        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    query,
                    (
                        await CompetitionChat.generate_ulid(),
                        ids_[0],
                        question,
                        answer,
                        user_id,
                    ),
                )

        return answer
