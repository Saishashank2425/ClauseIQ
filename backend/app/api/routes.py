from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.services.persistence import persist_analysis
from backend.app.schemas.analysis import DocumentAnalysis
from backend.app.services.analyzer import analyze_document

router = APIRouter(prefix="/api/v1", tags=["analysis"])
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


@router.post("/analyze", response_model=DocumentAnalysis)
async def analyze_contract(file: UploadFile = File(...), enable_ocr: bool = False, persist: bool = False, db: Session = Depends(get_db)) -> DocumentAnalysis:
    filename = file.filename or "contract"
    if not filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(status_code=415, detail="Only PDF and DOCX files are supported.")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds the 20 MB upload limit.")
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    try:
        analysis = analyze_document(filename, content, enable_ocr=enable_ocr)
        if persist:
            try:
                analysis.document_id = persist_analysis(db, filename, content, analysis)
            except Exception as exc:
                db.rollback()
                raise HTTPException(status_code=503, detail="Persistence failed. Check DATABASE_URL and initialize the database.") from exc
        return analysis
    except HTTPException:
        raise
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Document could not be processed: {type(exc).__name__}") from exc
