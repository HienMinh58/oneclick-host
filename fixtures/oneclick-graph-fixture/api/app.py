import os

import psycopg
import redis
from fastapi import FastAPI

app = FastAPI(title="OneClick Graph Fixture API")


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/db-check")
def db_check():
    database_url = os.environ["DATABASE_URL"]
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("select 1")
            value = cur.fetchone()[0]
    return {"postgres": value}


@app.get("/cache-check")
def cache_check():
    client = redis.Redis.from_url(os.environ["REDIS_URL"])
    client.set("oneclick:fixture", "ok", ex=60)
    return {"redis": client.get("oneclick:fixture").decode("utf-8")}
