# OneClick Graph Fixture

Small multi-service Docker Compose app for testing the OneClickHost Deployment Graph.

## Services

- `frontend`: static nginx app that calls the API.
- `api`: FastAPI app that connects to PostgreSQL and Redis.
- `worker`: background Python worker that depends on the API, PostgreSQL, and Redis.
- `db`: PostgreSQL database with a named volume.
- `redis`: Redis cache with a named volume.

## OneClick route suggestions

Use these public routes in OneClickHost:

| Service | Slug | Port | Health |
| --- | --- | --- | --- |
| `frontend` | `app` | `80` | `/` |
| `api` | `api` | `8000` | `/health` |

## Local run

```bash
docker compose up --build
```

Then open:

- Frontend: http://localhost:8080
- API: http://localhost:8000/health
