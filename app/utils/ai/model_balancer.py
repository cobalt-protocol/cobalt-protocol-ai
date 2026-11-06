from app.configs import settings
import requests


class ModelBalancer:
    @staticmethod
    async def get_available_models() -> list[dict]:
        response = requests.get(
            f"https://llm.chutes.ai/v1/models",
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

    @staticmethod
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
                f"{settings.base_url_chutes}chat/completions",
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

    @staticmethod
    async def find_first_healthy_model():
        """Memilih model termurah yang pertama kali lolos health check."""

        models = await ModelBalancer.get_available_models()

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

            if ModelBalancer.is_model_healthy(model_id):
                print(f"[SELECTED] {model_id}")
                return model_id

        raise RuntimeError("No healthy LLM model found.")
