# Striver SDE Tracker

Collaborative progress tracker for Striver's SDE Sheet built with Flask, Socket.IO, and MongoDB Atlas.

# SDE Tracker

Deployable Flask + MongoDB Atlas app with real‑time (Socket.IO) updates.

## Quick start (local)

1. Create a virtual environment and install requirements.
2. Create a `.env` with your MongoDB Atlas URI and names:

```
MONGO_URI=mongodb+srv://<user>:<pass>@<cluster>/<db>?retryWrites=true&w=majority
MONGO_DB_NAME=sdetrack
MONGO_COLLECTION_NAME=questions
USER_ONE_NAME=You
USER_TWO_NAME=Friend
```

3. Seed data:
```
python scripts/seed_data.py
```

4. Run locally:
```
python wsgi.py
```

## Deploy options

### Option A: Render (recommended – free tier, easy)

1. Push this repo to GitHub.
2. Create a new Render Web Service:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:$PORT wsgi:app`
   - Environment: `Python 3.12`
3. Add Environment Variables (same as your local `.env`).
4. Deploy. Render will expose a URL once the build finishes.

### Option B: Railway (simple, generous free tier)

1. Import the repo in Railway.
2. Set service variables: `MONGO_URI`, `MONGO_DB_NAME`, `MONGO_COLLECTION_NAME`, `USER_ONE_NAME`, `USER_TWO_NAME`.
3. Set Start Command: `gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:$PORT wsgi:app`.
4. Deploy.

### Option C: Docker anywhere (AWS Lightsail, Azure App Service, Fly.io, etc.)

Build and run the included Dockerfile:

```
docker build -t sdetrack .
docker run -p 8000:8000 --env-file .env sdetrack
```

Set your platform’s env vars the same as `.env`.

### Option D: Heroku (uses Procfile)

Heroku free dynos are gone, but if you have an account with credits:

```
heroku create
heroku buildpacks:set heroku/python
heroku config:set MONGO_URI=... MONGO_DB_NAME=sdetrack MONGO_COLLECTION_NAME=questions USER_ONE_NAME=You USER_TWO_NAME=Friend
git push heroku main
```

Files already provided for deploy:
- `Procfile` – Gunicorn + eventlet worker
- `runtime.txt` – Python 3.12.1
- `Dockerfile` and `.dockerignore`

## Notes

- Socket.IO requires long‑lived connections; that’s why we use Gunicorn with the `eventlet` worker class.
- If you see a `403 websocket` on some hosts, enable websockets in your service settings.
- Real-time progress updates for two collaborators via WebSockets
- Day-wise breakdown of all questions in Striver's SDE Sheet

1. Create a Python virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Duplicate `.env.example` (see below) and set MongoDB Atlas credentials.
3. Seed the database with the provided dataset:
   ```bash
   .\.venv\Scripts\python scripts\seed_data.py
   ```
4. Run the development server:
   ```bash
   .\.venv\Scripts\python wsgi.py
## Environment Variables

Create `.env` using the template below:

```
MONGO_URI=mongodb+srv://<username>:<password>@<cluster_url>/sde_tracker?retryWrites=true&w=majority
MONGO_DB_NAME=sde_tracker
MONGO_COLLECTION_NAME=questions
USER_ONE_NAME=You
USER_TWO_NAME=Friend
```

## Deployment

- For Render/Railway/Heroku, push this repository and set environment variables in the dashboard.
- The provided `Procfile` runs the app with Gunicorn and Eventlet for WebSocket support.
- Ensure the cluster IP allow-list permits the hosting platform.

## Data Source Disclaimer

The Striver SDE Sheet question metadata included in this repository is reproduced for personal tracking use. Please review and respect the original author's terms when distributing or deploying this project.
