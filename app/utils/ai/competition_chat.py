import requests
import io
from openai import OpenAI
import base64
import pymupdf
from app.configs import settings
from pathlib import Path
from app.utils.ai import ModelBalancer
import re
import ast
import json
import psycopg
from app.utils.langchain_embed import embeddings


class CompetitionChat:
    FORMAT_GAMBAR = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }

    client = OpenAI(
        api_key=settings.api_key_chutes,
        base_url=settings.base_url_chutes,
    )

    @staticmethod
    async def bersihkan_output(teks):
        teks = "\n".join(baris.strip() for baris in teks.splitlines())

        teks = re.sub(r"\n{3,}", "\n\n", teks)

        return teks.strip()

    @staticmethod
    async def analisis_dokumen(path, pertanyaan, max_pages=None):
        if isinstance(path, io.BytesIO):

            dokumen = pymupdf.open(stream=path.getvalue(), filetype="pdf")

        elif isinstance(path, (bytes, bytearray)):

            dokumen = pymupdf.open(stream=path, filetype="pdf")

        else:

            path = Path(path)
            ekstensi = path.suffix.lower()

            if not path.exists():
                raise FileNotFoundError(f"File tidak ditemukan: {path}")

            if ekstensi != ".pdf" and ekstensi not in CompetitionChat.FORMAT_GAMBAR:
                raise ValueError("Format harus PDF, PNG, JPG, JPEG, atau WEBP.")

            dokumen = pymupdf.open(str(path))

        try:

            # 2. Batasi jumlah halaman
            jumlah_halaman = len(dokumen)

            if max_pages is not None:
                jumlah_halaman = min(jumlah_halaman, max_pages)

            konteks_teks = []
            konten_visual = []

            # 3. Extract teks dan render gambar
            for i in range(jumlah_halaman):

                halaman = dokumen[i]

                # Extract text
                teks = halaman.get_text("text").strip()

                if teks:
                    konteks_teks.append(f"Halaman {i + 1}:\n{teks}")

                # Render halaman menjadi gambar
                pix = halaman.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)

                gambar = base64.b64encode(pix.tobytes("png")).decode("utf-8")

                konten_visual.append(
                    {"type": "text", "text": f"Visual halaman {i + 1}:"}
                )

                konten_visual.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{gambar}"},
                    }
                )

            teks_pdf = "\n\n".join(konteks_teks)

            if not teks_pdf:
                teks_pdf = (
                    "Tidak ada teks yang berhasil diekstrak. "
                    "Gunakan gambar untuk membaca dokumen."
                )

        finally:
            dokumen.close()

        # 5. Gabungkan pertanyaan, teks, dan gambar
        konten_user = [
            {
                "type": "text",
                "text": (
                    "Kamu bertugas memahami dan menjawab pertanyaan "
                    "berdasarkan dokumen yang diberikan.\n\n"
                    f"PERTANYAAN:\n{pertanyaan}\n\n"
                    f"ISI DOKUMEN:\n{teks_pdf}\n\n"
                    "ATURAN PENILAIAN:\n"
                    "1. relevan = y jika topik atau maksud pertanyaan "
                    "berhubungan dengan isi, tujuan, objek, atau pembahasan dokumen.\n"
                    "2. relevan = n jika pertanyaan sama sekali tidak "
                    "berhubungan dengan dokumen.\n"
                    "3. status = not_found jika pertanyaan relevan "
                    "tetapi informasi yang diminta tidak ditemukan.\n\n"
                    "ATURAN MENJAWAB:\n"
                    "- Jika relevan = y, jawab pertanyaan berdasarkan dokumen.\n"
                    "- Jika relevan = n, jawab bahwa pertanyaan tidak relevan "
                    "dengan dokumen, kemudian berikan ringkasan singkat dokumen.\n"
                    "- Jika status = not_found, jelaskan bahwa informasi "
                    "tidak ditemukan dalam dokumen.\n"
                    "- Jangan mengarang informasi.\n"
                    "- Gunakan teks dan visual sebagai sumber informasi.\n\n"
                    "FORMAT OUTPUT WAJIB JSON:\n"
                    "{\n"
                    '  "relevan": "y atau n",\n'
                    '  "status": "answered atau not_found atau irrelevant",\n'
                    '  "jawaban": "jawaban atau penjelasan"\n'
                    "}\n\n"
                    "Jangan gunakan Markdown code block. "
                    "Jangan memberikan teks di luar JSON."
                ),
            }
        ]

        konten_user.extend(konten_visual)

        model_id = await ModelBalancer.find_first_healthy_model()

        response = CompetitionChat.client.chat.completions.create(
            model=model_id,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Kamu adalah document understanding assistant. "
                        "Tugasmu mengidentifikasi hubungan pertanyaan dengan "
                        "dokumen, kemudian menjawab berdasarkan bukti tekstual "
                        "dan visual. Jangan menyimpulkan bahwa pertanyaan tidak "
                        "relevan hanya karena jawaban spesifiknya tidak ditemukan. "
                        "Selalu keluarkan JSON valid."
                    ),
                },
                {"role": "user", "content": konten_user},
            ],
            response_format={"type": "json_object"},
            max_tokens=1500,
        )

        return await CompetitionChat.bersihkan_output(
            response.choices[0].message.content or ""
        )

    @staticmethod
    async def download_pdf(url):
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        pdf_memory = io.BytesIO(response.content)

        return pdf_memory

    @staticmethod
    async def query_rag_question(question: str, top_k: int = 3):
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
    Similarity: {row[3]:.4f}
    """ for row in rows)

        return context

    @staticmethod
    async def tanya_competition(question: str, competition_id: str):
        prompt_template = """
Jawab pertanyaan berdasarkan konteks berikut.

Aturan:
- Untuk Konteks kompetisi/perlombaan/hackathonnya id nya adalah {competition_id}
- Jika pertanyaan tidak sesuai konteks. outputnya saya tidak tahu
- Tolong jawab pertanyaan sesuai kompetisi id : {competition_id}
- Jika user mention kompetisi id, dan tidak sama dengan {competition_id}. outputnya saya tidak tahu
- Pada output jangan menyebutkan kompetisi id

Konteks:
{context}

Pertanyaan:
{question}
"""

        context = await CompetitionChat.query_rag_question(question)

        prompt = (
            prompt_template.replace("{context}", context)
            .replace("{question}", question)
            .replace("{competition_id}", competition_id)
        )

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

        return result["choices"][0]["message"]["content"]

    @staticmethod
    async def result_chat(question, competition_id, guidebook_url):
        pdf_memory = await CompetitionChat.download_pdf(guidebook_url)
        result = await CompetitionChat.analisis_dokumen(
            path=pdf_memory, pertanyaan=question
        )
        try:
            json_jawaban = ast.literal_eval(result)
        except SyntaxError:
            json_jawaban = json.loads(result)
        if (
            json_jawaban["status"] == "not_found"
            or json_jawaban["status"] == "inrelevant"
            or json_jawaban["relevan"] == "n"
        ):
            result = await CompetitionChat.tanya_competition(question, competition_id)
        else:
            result = json_jawaban["jawaban"]
        return result
