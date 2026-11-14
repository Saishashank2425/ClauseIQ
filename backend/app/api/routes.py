from fastapi import APIRouter, File, HTTPException, UploadFile
from backend.app.schemas.analysis import DocumentAnalysis
from backend.app.services.analyzer import analyze_document

router = APIRouter(prefix="/api/v1", tags=["analysis"])
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


@router.post("/analyze", response_model=DocumentAnalysis)
async def analyze_contract(file: UploadFile = File(...), enable_ocr: bool = False) -> DocumentAnalysis:
    filename = file.filename or "contract"
    if not filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(status_code=415, detail="Only PDF and DOCX files are supported.")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds the 20 MB upload limit.")
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    try:
        return analyze_document(filename, content, enable_ocr=enable_ocr)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Document could not be processed: {type(exc).__name__}") from exc
