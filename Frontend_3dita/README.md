# 3DITA Reconstruction Demo

This workspace contains a React + Vite frontend and a local FastAPI backend stub.

## Run locally

1. Install backend dependencies:

```powershell
cd backend
python -m pip install -r requirements.txt
```

2. Install frontend dependencies:

```powershell
cd frontend
npm install
```

3. Start both services:

```powershell
cd c:\Frontend_3dita
run.bat
```

4. Open the frontend app in your browser at the URL shown by Vite.

## What is integrated

- Frontend uses `VITE_API_URL=http://localhost:8010`
- Backend stub exposes:
  - `GET /health`
  - `POST /api/reconstruct`
  - `GET /api/job/{job_id}`
  - `WS /ws/job/{job_id}`

The backend simulates reconstruction progress and serves sample `.ply` files.
