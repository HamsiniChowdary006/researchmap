# ResearchMap

ResearchMap turns a research topic into an evidence-oriented map of the field. It discovers relevant papers from arXiv, ranks them by relevance, extracts structured findings with Gemini, synthesizes the results into a landscape, and produces a suggested reading list with direct arXiv links.

The project runs locally as two services:

- **Frontend:** Next.js and React at `http://localhost:3000`
- **Backend:** FastAPI at `http://127.0.0.1:8011`
- **Database:** SQLite at `data/researchmap.db`

## Features

- Topic-based arXiv paper discovery
- Cross-encoder relevance ranking
- Structured extraction of each paper's problem, method, results, contribution, limitations, and techniques
- Gemini-powered synthesis of clusters, relationships, tensions, and open problems
- Reading list with:
  - Paper titles
  - Direct arXiv links
  - Existing relevance scores
  - Suggested reading order
  - A reason for each paper's position
- Background job progress reporting by pipeline stage
- Detailed backend logging for arXiv and Gemini failures
- arXiv timeout and retry handling
- Local SQLite persistence for jobs, papers, extractions, and landscapes

## How It Works

When a user submits a topic, the backend creates a job and runs these stages:

1. **Discover:** Fetches candidate papers from arXiv.
2. **Rank:** Scores candidates with `cross-encoder/ms-marco-MiniLM-L-6-v2`.
3. **Extract:** Downloads paper content and asks Gemini for structured findings. Cached extractions are reused when available.
4. **Synthesize:** Asks Gemini to organize the extracted findings into clusters, relationships, tensions, and open problems.
5. **Reading list:** Builds an ordered list from the ranked papers that contributed successful extractions. Survey and review papers are prioritized when identifiable; remaining papers are ordered by relevance score.

The browser communicates only with the local FastAPI service. arXiv and Gemini requests are made server-side.

## Requirements

Install the following before starting:

- Python 3.11 or newer
- Node.js 20 or newer
- npm
- A Gemini API key
- Network access to arXiv and the Gemini API during discovery and synthesis

## Setup

### 1. Clone and enter the repository

```powershell
git clone https://github.com/HamsiniChowdary006/researchmap.git
Set-Location researchmap
```

### 2. Create the Python environment

Windows PowerShell:

```powershell
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
```

If PowerShell blocks activation, use the virtual environment's executable directly in later commands:

```powershell
& .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

### 3. Configure environment variables

Copy the example file:

```powershell
Copy-Item .env.example .env
```

Open `.env` and replace `your_key_here` with a valid Gemini API key:

```dotenv
GEMINI_API_KEY=your_key_here
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8011
```

Never commit `.env`. It is ignored by Git. `.env.example` contains placeholders only.

### 4. Install frontend dependencies

```powershell
Set-Location frontend
npm install
Set-Location ..
```

## Run Locally

Start the backend from the repository root in one terminal:

```powershell
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8011
```

Start the frontend from the repository root in a second terminal:

```powershell
Set-Location frontend
npm run dev
```

Open the application at:

```text
http://localhost:3000
```

The FastAPI interactive API documentation is available at:

```text
http://127.0.0.1:8011/docs
```

## Verify the Services

Check the backend health endpoint:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8011/health
```

Expected response:

```json
{"status":"ok"}
```

Check that the frontend is responding:

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:3000
```

Both services should return HTTP `200` responses.

## API Reference

### `GET /health`

Returns backend availability.

### `POST /api/search`

Creates a background research job.

Request body:

```json
{
  "topic": "efficient multimodal agents",
  "papers_per_search": 8
}
```

Constraints:

- `topic` must contain at least two characters.
- `papers_per_search` must be between `1` and `40`.

Response:

```json
{
  "job_id": "job-uuid"
}
```

### `GET /api/jobs/{job_id}`

Returns the job status and the status of each pipeline stage. Failed stages include their error message.

### `GET /api/landscape/{job_id}`

Returns the completed landscape, including:

- `clusters`
- `relationships`
- `tensions`
- `open_problems`
- `reading_list`

Each reading-list item includes its order, arXiv ID, title, direct URL, relevance score, and placement reason.

### `GET /api/papers/{arxiv_id}`

Returns stored metadata for a paper and its structured extraction when available.

## Project Structure

```text
researchmap/
├── backend/
│   ├── app/
│   │   ├── db.py             # SQLite schema and connection helpers
│   │   ├── main.py           # FastAPI application and API routes
│   │   ├── pipeline.py       # Background research pipeline
│   │   └── schemas.py        # Pydantic response models
│   ├── scripts/
│   │   ├── fetch.py          # arXiv discovery with timeout and retries
│   │   ├── rerank.py         # Cross-encoder relevance ranking
│   │   ├── ingest.py         # Paper download and text extraction
│   │   ├── extract.py        # Gemini paper extraction
│   │   └── synthesize.py     # Gemini landscape synthesis
│   └── requirements.txt
├── data/
│   └── pdfs/                 # Local paper text cache
├── frontend/
│   └── src/app/              # Next.js application UI
├── .env.example
└── README.md
```

## Development Checks

Run the backend syntax check:

```powershell
& .\.venv\Scripts\python.exe -m compileall backend\app backend\scripts
```

Run frontend linting:

```powershell
Set-Location frontend
npm run lint
```

Build the frontend locally:

```powershell
npm run build
```

Run the frontend dependency audit without modifying packages:

```powershell
npm audit
```

## Troubleshooting

### The browser reports `Failed to fetch`

Confirm that:

1. The backend is running on port `8011`.
2. The frontend is running on port `3000`.
3. `NEXT_PUBLIC_API_BASE_URL` points to `http://127.0.0.1:8011`.
4. The backend CORS configuration allows the frontend origin.
5. The backend terminal does not show an arXiv or Gemini error.

Both `http://localhost:3000` and `http://127.0.0.1:3000` are allowed for local development.

### Gemini errors

Confirm that `GEMINI_API_KEY` is present in `.env` and valid. The backend logs the operation, provider status when available, response body, and error message. Do not paste the API key into source files, issues, or chat logs.

### arXiv requests time out

The discovery stage uses a 45-second timeout and retries up to three times with backoff. Check network access and review the backend logs for the specific failure details.

### First run is slow

The ranking stage may download the sentence-transformers model the first time it runs. Later runs can reuse the local model cache.

### A job fails after papers are found

Open `GET /api/jobs/{job_id}` and inspect the stage errors. Paper metadata and successful extractions are stored in SQLite, so rerunning can reuse cached work.

## Security Notes

- Keep `.env` local and out of Git.
- Use `.env.example` as the only committed environment template.
- Do not log or commit API key values.
- The application is configured for local development origins only.
- Generated databases, caches, downloaded paper content, virtual environments, and frontend build output are ignored by Git.

## License

No license has been specified for this project yet.
