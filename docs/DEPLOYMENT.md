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

## Google sign-in
The web app uses Google Identity Services. Create an OAuth 2.0 Client ID of type **Web application** in Google Cloud Console and add the exact Render origin (for example `https://clauseiq-ilky.onrender.com`) to **Authorized JavaScript origins**. Set the resulting client ID as `GOOGLE_CLIENT_ID` in the Render service environment. No client secret is used by this ID-token flow. The frontend sends the Google ID token to `POST /api/v1/auth/google`; the backend verifies its signature and audience. Uploaded-document analysis and Q&A require a verified Google ID token in the `Authorization: Bearer <id_token>` header. ID tokens are held in session storage and expire; users may need to sign in again.

## Sample RAG workspace
Use **Explore sample contract** in the app or call `GET /api/v1/demo` to load a synthetic SaaS services agreement. Ask questions through `POST /api/v1/demo/ask` with JSON `{\"question\":\"What is the indemnity exposure?\"}`. This sample endpoint is public and uses synthetic data only; it exercises the same hybrid retrieval and evidence-return path without requiring login or a file upload.

## API
- `GET /`, `GET /health`: service status.
- `GET /api/v1/auth/config`, `POST /api/v1/auth/google`: Google sign-in configuration and token verification.
- `GET /api/v1/demo`, `POST /api/v1/demo/ask`: public synthetic demo corpus and grounded sample Q&A.
- `POST /api/v1/analyze`: multipart `file` (PDF/DOCX), optional query flags `enable_ocr` and `persist`; requires Google sign-in.
- `POST /api/v1/ask`: multipart `file` and `question`, optional query flag `enable_ocr`; requires Google sign-in.

OCR requires the Tesseract executable installed on the host. The Python package alone is not the OCR engine.

## Production checklist
Tenant isolation, restrictive CORS, rate limiting, malware scanning, private object storage, audit logging, retention/deletion controls, secret rotation, database backups and expert-reviewed model evaluation are not included in this educational prototype. Google sign-in verifies identity but does not yet provide organization membership, role-based access or tenant-level authorization. Do not treat this research demo as production legal infrastructure.
