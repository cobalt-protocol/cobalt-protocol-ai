from langchain_redis import RedisVectorStore, RedisConfig
import redis
from app.utils.langchain_embed import embeddings
from app.configs.settings import settings

redis_config = RedisConfig(
    index_name="my_db",
    redis_url=settings.redis_url,
    distance_metric="COSINE",
)

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

vector_store = RedisVectorStore(embeddings, config=redis_config)
