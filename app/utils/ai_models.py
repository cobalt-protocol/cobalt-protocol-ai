from app.configs import settings
import requests
from app.utils.query_rag import query_rag

prompt_template = """
Jawab pertanyaan berdasarkan konteks berikut.

Kamu Di Tugaskan untuk memberikan list rekomendasi team terbaik berdasarkan konteks.

Aturan:
- Kembalikan dalam bentuk tipe data array yang di dalamnya ada key dan value yang valid, untuk keynya hanya ada team_id
- Output Jangan di bungkus pakai apapun itu, pastikan outputnya bersih
- Setiap team_id harus berupa string.
- Jangan menambahkan spasi di awal atau akhir team_id.
- Jangan menambahkan penjelasan di luar array.
- Jika tidak ditemukan, kembalikan [].
- Jika dia bertanya untuk spesifik team butuh orang seperti apa, kembalikan []

Output:
- Berikut contoh output data yang tepat : [{'team_id':'01M5Y32MGGJYQ56XP29D7QRW7N'}].

Konteks:
{context}

Pertanyaan:
{question}
"""


def get_available_models() -> list[dict]:
    response = requests.get(
        f"{settings.base_url_chutes}/models",
        headers={
            "Authorization": f"Bearer {settings.api_key_chutes}",
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    response.raise_for_status()

    models = []

    for item in response.json().get("data", []):
        model_id = item.get("id")

        if not model_id:
            continue

        features = item.get("supported_features", [])

        # Skip model embedding
        if any("embed" in str(feature).lower() for feature in features):
            continue

        pricing = item.get("pricing", {})

        models.append(
            {
                "model": model_id,
                "context_length": item.get("context_length"),
                "max_output_length": item.get("max_output_length"),
                "input_price_per_1m": pricing.get("prompt"),
                "output_price_per_1m": pricing.get("completion"),
                "input_modalities": item.get("input_modalities"),
                "output_modalities": item.get("output_modalities"),
                "supported_features": features,
            }
        )

    return models


def is_model_healthy(model_id: str) -> bool:
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": "Reply with OK."}],
        "max_tokens": 8,
        "temperature": 0,
        "stream": False,
    }

    try:
        response = requests.post(
            f"{settings.base_url_chutes}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.api_key_chutes}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )

        if not response.ok:
            print(f"[SKIP] {model_id}: HTTP {response.status_code}")
            return False

        data = response.json()
        choices = data.get("choices", [])

        if not choices:
            return False

        content = choices[0].get("message", {}).get("content")
        if not isinstance(content, str) or not content.strip():
            return False

        print(f"[READY] {model_id}")
        return True

    except (requests.RequestException, ValueError) as exc:
        print(f"[SKIP] {model_id}: {exc}")
        return False


def find_first_healthy_model():
    """Memilih model termurah yang pertama kali lolos health check."""

    models = get_available_models()

    if not models:
        raise RuntimeError("No candidate models found.")

    # Urutkan berdasarkan harga input + output
    models = sorted(
        models,
        key=lambda m: (
            float(m.get("input_price_per_1m") or float("inf"))
            + float(m.get("output_price_per_1m") or float("inf"))
        ),
    )

    print(f"Available candidates: {len(models)}")

    for item in models:
        model_id = item["model"]

        input_price = item.get("input_price_per_1m")
        output_price = item.get("output_price_per_1m")

        print(
            f"[CHECK] {model_id} | "
            f"Input: {input_price} | "
            f"Output: {output_price}"
        )

        if is_model_healthy(model_id):
            print(f"[SELECTED] {model_id}")
            return model_id

    raise RuntimeError("No healthy LLM model found.")


def tanya_rag(question: str):
    # 1. Ambil konteks dari hasil query
    context = query_rag(question)

    # 2. Masukkan konteks dan pertanyaan ke prompt
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

    model_id = find_first_healthy_model()

    # 3. Kirim prompt ke LLM
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
