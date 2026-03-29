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

**Terminal 1 — Flask backend (port 8080):**
```bash
make run
```

**Terminal 2 — Streamlit dashboard (port 8501):**
```bash
streamlit run services/frontend/dashboard.py
```

Open `http://localhost:8501` in your browser.

**ADK Dev UI (shows agent traces and parallel execution):**
```bash
adk web
# → http://localhost:8000
# Select "relieflink_agents" and run the pipeline
```

---

## Running Tests

```bash
make test              # All tests
make test-unit         # Unit tests only
make test-integration  # Integration tests (calls live FEMA/NOAA APIs)
make test-coverage     # Tests with coverage report
```

---

## Deploy to Cloud Run

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
