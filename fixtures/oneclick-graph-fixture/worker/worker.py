import os
import time

import psycopg
import redis
import requests


def run_once():
    redis.Redis.from_url(os.environ["REDIS_URL"]).set("oneclick:worker", "alive", ex=30)
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute("select 1")
            cur.fetchone()
    requests.get(f"{os.environ['API_URL']}/health", timeout=5).raise_for_status()


while True:
    run_once()
    time.sleep(15)
