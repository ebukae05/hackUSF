# ReliefLink

Equity-first disaster resource coordination powered by multi-agent AI. Matches available relief resources to community needs, prioritizing vulnerable communities first using CDC Social Vulnerability Index data.

For full architecture, requirements, and design decisions, see [`docs/SYSTEM_DESIGN.md`](docs/SYSTEM_DESIGN.md).

## Setup

```bash
git clone https://github.com/ebukae05/hackUSF.git
cd hackUSF
pip install -r requirements.txt
cp .env.example .env   # Add your Gemini API key
make run               # Start dev server on port 8080
```

## Teardown

```bash
# Stop the dev server: Ctrl+C

# Remove Cloud Run deployment (if deployed)
gcloud run services delete relieflink-hackathon --region us-central1 --quiet
```
