# Run and deploy ClauseIQ

## Local development
Use Python 3.13. Backend terminal:
```powershell
python -m venv venv
.\venv\Scripts\activate
python -m pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```
Open `http://127.0.0.1:8000/docs`.

Frontend terminal:
```powershell
cd frontend
npm install
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"
npm run dev
```

## Vercel (two projects)
Deploy the API and frontend as separate Vercel projects from the same GitHub repository.

### API project
- Repository: `Saishashank2425/ClauseIQ`
- Root directory: repository root
- Framework: Other
- Production branch: `implementation-core`
- The root `vercel.json` routes requests to `api/index.py`.
- After deployment, check `/health` and `/docs`.

### Frontend project
- Import the same repository as a second Vercel project.
- Root directory: `frontend`
- Framework preset: Vite; build command `npm run build`; output directory `dist`.
- Set `VITE_API_BASE_URL` to the deployed API origin, for example `https://YOUR-API-PROJECT.vercel.app`.
- Redeploy after setting the environment variable.

The API has permissive CORS for a cookie-free demo. Before production, replace wildcard CORS with the exact frontend origin. Vercel serverless request/runtime limits are stricter than the local 20 MB application limit (notably, request bodies around 4.5 MB can be rejected by the platform before FastAPI receives them). Do not use the serverless API for large contracts, OCR-heavy PDFs, or transformer inference.

## Docker / persistent hosting
```powershell
docker compose up --build -d
docker compose exec api alembic upgrade head
```
The API is available on port 8000. This is the preferred baseline for larger files and optional ML workloads. Configure secrets using the hosting provider's environment-variable manager, not committed files.

## Environment variables
See `.env.example`. Optional components:
- `CLAUSEIQ_DENSE_MODEL`: sentence-transformer embedding model; requires `requirements-ml.txt`.
- `CLAUSEIQ_CROSS_ENCODER_MODEL`: optional reranker; requires `requirements-ml.txt`.
- `CLAUSEIQ_CLASSIFIER_BACKEND=legalbert`: load a locally fine-tuned Legal-BERT artifact.
- `CLAUSEIQ_LLM_BASE_URL`, `CLAUSEIQ_LLM_MODEL`, `CLAUSEIQ_LLM_API_KEY`: optional OpenAI-compatible grounded generation endpoint.

## API
- `GET /`, `GET /health`: service status.
- `POST /api/v1/analyze`: multipart `file` (PDF/DOCX), optional query flags `enable_ocr` and `persist`.
- `POST /api/v1/ask`: multipart `file` and `question`, optional query flag `enable_ocr`.

OCR requires the Tesseract executable installed on the host. The Python package alone is not the OCR engine.

## Production checklist
Authentication/authorization, tenant isolation, restrictive CORS, rate limiting, malware scanning, private object storage, audit logging, retention/deletion controls, secret rotation, database backups and expert-reviewed model evaluation are not included in this educational prototype.
