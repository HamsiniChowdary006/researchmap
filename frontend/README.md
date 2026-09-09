## ResearchMap Local Setup

ResearchMap runs locally as a Next.js frontend and a FastAPI backend.

From the repository root, create the environment file:

```powershell
Copy-Item .env.example .env
```

Open `.env` and set `GEMINI_API_KEY` to a valid Gemini API key. Keep `.env` local; it is ignored by Git.

Start the backend from the repository root:

```powershell
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8011
```

Start the frontend in a second terminal:

```powershell
Set-Location frontend
npm install
npm run dev
```

Open `http://localhost:3000`. The backend API is available at `http://127.0.0.1:8011`, with health checks at `/health`.

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.
