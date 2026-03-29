# ReliefLink

Equity-first disaster resource coordination powered by multi-agent AI. Matches available relief resources to community needs, prioritizing vulnerable communities first using CDC Social Vulnerability Index data.

For full architecture, requirements, and design decisions, see [`docs/SYSTEM_DESIGN.md`](docs/SYSTEM_DESIGN.md).

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GOOGLE_API_KEY` | Yes (for routing plans) | — | Gemini 2.5 Flash API key. Without it, routing plans show "Pending" but the full pipeline still runs. |
| `GOOGLE_GENAI_USE_VERTEXAI` | No | `FALSE` | Set to `TRUE` only if using Vertex AI instead of direct Gemini API. |
| `RELIEFLINK_BACKEND_URL` | No | `http://127.0.0.1:8080` | URL the Streamlit dashboard uses to reach the Flask backend. Override when backend is on Cloud Run. |
| `PROJECT_ID` | For deploy only | — | GCP project ID. Required for `make deploy`. |
| `SECRET_NAME` | For deploy only | `gemini-api-key` | Secret Manager secret name holding the Gemini API key. |

---

## Setup

```bash
git clone https://github.com/ebukae05/hackUSF.git
cd hackUSF
pip install -r requirements.txt
cp .env.example .env        # Add your GOOGLE_API_KEY
```

---

## Running Locally

The backend and dashboard run as two separate processes.

### Mac / Linux

**Terminal 1 — Flask backend (port 8080):**
```bash
make run
```

**Terminal 2 — Streamlit dashboard (port 8501):**
```bash
streamlit run services/frontend/dashboard.py
```

**Terminal 3 — ADK Dev UI (port 8000) — required for demo judges:**
```bash
adk web services/
# → http://localhost:8000
# Select "relieflink_agents" → run pipeline → shows parallel + loop agent execution
```

### Windows

`make` is not available on Windows by default. Use these commands instead:

**Terminal 1 — Flask backend (port 8080):**
```bash
python -m flask --app services.backend.app run --port 8080 --debug
```

**Terminal 2 — Streamlit dashboard (port 8501):**
```bash
streamlit run services/frontend/dashboard.py
```

**Terminal 3 — ADK Dev UI (port 8000) — required for demo judges:**

`adk` may not be on your PATH on Windows. Fix it once, then it works everywhere:

```bash
# Step 1 — find your Scripts folder
python -c "import sysconfig; print(sysconfig.get_path('scripts'))"

# Step 2 — add it to PATH in Git Bash (replace with your actual path)
export PATH="/c/Users/<YourName>/AppData/Roaming/Python/Python3xx/Scripts:$PATH"

# Step 3 — run
adk web services/
```

> **Windows note:** If the pipeline fails with an asyncio error, add the following to the top of `services/relieflink_agents/orchestrator.py` before running:
> ```python
> import asyncio, sys
> if sys.platform == "win32":
>     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
> ```

Open `http://localhost:8501` in your browser.

---

## Running Tests

```bash
# Mac / Linux
make test
make test-unit
make test-integration
make test-coverage

# Windows
python -m pytest tests/
python -m pytest tests/unit/
python -m pytest tests/integration/
python -m pytest tests/ --cov=services --cov-report=term-missing
```

---

## Deploy to Cloud Run

> **Mac / Linux only.** Windows users: use Git Bash or WSL to run the deploy script.

**Prerequisites:**
```bash
# 1. Install and authenticate gcloud
gcloud auth login
gcloud auth configure-docker

# 2. Enable required APIs
gcloud services enable run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com

# 3. Create Artifact Registry repo
gcloud artifacts repositories create relieflink --repository-format=docker --location=us-central1

# 4. Store Gemini API key in Secret Manager
echo -n "YOUR_GEMINI_API_KEY" | gcloud secrets create gemini-api-key --data-file=-
```

**Deploy:**
```bash
PROJECT_ID=<your-gcp-project-id> make deploy
```

**Point dashboard at Cloud Run backend:**
```bash
RELIEFLINK_BACKEND_URL=https://<your-cloud-run-url> streamlit run services/frontend/dashboard.py
```

---

## Teardown

```bash
# Stop local processes: Ctrl+C in each terminal

# Remove Cloud Run deployment (if deployed)
gcloud run services delete relieflink --region us-central1 --quiet
```
