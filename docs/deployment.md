# Deployment

## Local (no Docker)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt -r ml/requirements.txt -r frontend/requirements.txt
cp .env.example .env

python ml/generate_synthetic_data.py
python ml/train_anomaly_models.py

# terminal 1
uvicorn app.main:app --reload --app-dir backend

# terminal 2
CYBERSENTINEL_API_URL=http://localhost:8000/api/v1 streamlit run frontend/app.py
```

## Docker
```bash
docker compose up --build
# backend: http://localhost:8000/docs
# frontend: http://localhost:8501
```
To use real PostgreSQL instead of SQLite:
```bash
# in .env: set POSTGRES_PASSWORD and DATABASE_URL=postgresql+psycopg://cybersentinel:<pw>@postgres:5432/cybersentinel
docker compose --profile postgres up --build
```

**Status of this file's commands:** written to spec and internally
consistent with the Dockerfiles/compose file, but `docker build` /
`docker compose up` could not be executed in the development sandbox (no
Docker daemon, no network to pull the `python:3.11-slim` / `postgres:16-alpine`
base images). Treat the Docker section as "should work, verify first" — the
`.github/workflows/ci.yml` `docker-build` job will do that verification on
every push once this repo is on GitHub.

## Streamlit Community Cloud (frontend only)
The spec's overall preference for a Streamlit-based deployment path:
1. Push this repo to GitHub.
2. Deploy the **backend** somewhere it can run continuously with a
   persistent disk (Render, Railway, Fly.io, a VM, etc.) — Streamlit
   Community Cloud only hosts the Streamlit app itself, not the FastAPI
   backend + database.
3. On share.streamlit.io, create an app pointing at `frontend/app.py`,
   with `frontend/requirements.txt` as the requirements file.
4. Set the `CYBERSENTINEL_API_URL` app secret/environment variable to the
   deployed backend's public URL + `/api/v1`.

If you want a single URL with no separate backend host, the alternative is
to deploy the whole `docker-compose.yml` stack to a platform that runs
Docker Compose directly (Railway, Render's Docker Compose support, a small
VM) rather than trying to run FastAPI+SQLite from inside Streamlit Cloud's
process, which isn't designed for a second long-running server.

## Environment variables required in production
See `.env.example`. At minimum: `SECRET_KEY` (generate a real random
value), `DATABASE_URL` if not using SQLite, and `CORS_ALLOW_ORIGINS` set to
the real frontend URL.
