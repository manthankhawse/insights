import redis

r = redis.Redis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), decode_responses=True)

def process_dataset(id: str):
    r.lpush('datasource', id)
