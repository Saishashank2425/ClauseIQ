# Running and deploying ClauseIQ

## Backend (local)
Use Python 3.13:
```powershell
python -m venv venv
.\venv\Scripts\activate
python -m pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```
Open `http://127.0.0.1:8000/docs`.

## Frontend (local)
In a second terminal:
```powershell
cd frontend
npm install
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"
npm run dev
```
Open the Vite URL shown in the terminal.

## Vercel deployment
Create two Vercel projects from this repository:

### API project
- Repository: `Saishashank2425/ClauseIQ`
- Root Directory: repository root
- Framework preset: Other (Python serverless function)
- Production branch: the branch containing the backend and `api/index.py`
- Deploy. Verify `/health` and `/docs`.

### Frontend project
- Import the same repository as a second Vercel project.
- Root Directory: `frontend`
- Framework preset: Vite
- Build command: `npm run build`
- Output directory: `dist`
- Environment variable: `VITE_API_BASE_URL=https://YOUR-API-PROJECT.vercel.app`
- Redeploy after setting the variable.

The API currently enables wildcard CORS for a cookie-free public demo. Before production, restrict `allow_origins` to the exact frontend domain and add authentication, rate limits, malware scanning, and privacy controls.

## API
- `GET /` and `GET /health`: service status
- `POST /api/v1/analyze`: multipart `file` (PDF/DOCX), optional `enable_ocr`
- `POST /api/v1/ask`: multipart `file` and `question`, optional `enable_ocr`

OCR additionally requires the Tesseract executable installed on the backend host. OCR is not guaranteed to work on a serverless host without bundling the binary.

## Important limitations
- Risk flags are transparent phrase heuristics, not a trained legal classifier.
- Q&A uses BM25 to retrieve source passages and returns evidence; it does not generate legal conclusions.
- PDF page provenance is preserved. DOCX page numbers are unavailable through python-docx.
- SQLAlchemy models are included as a persistence foundation; document persistence is not yet wired into the API.
- Vercel serverless functions have execution and payload limits. Large contracts, OCR-heavy scans, model inference, and long-running jobs should move to a persistent backend/worker service.
