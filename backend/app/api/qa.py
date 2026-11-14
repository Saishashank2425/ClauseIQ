from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from backend.app.services.analyzer import analyze_document
from backend.app.rag.answer import answer_question
from backend.app.api.auth import require_user

qa_router = APIRouter(prefix="/api/v1", tags=["question answering"])
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

@qa_router.post("/ask")
async def ask_contract(question: str = Form(...), file: UploadFile = File(...), enable_ocr: bool = False, user: dict = Depends(require_user)):
    filename = file.filename or "contract"
    if not filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(status_code=415, detail="Only PDF and DOCX files are supported.")
    if not question.strip() or len(question) > 1500:
        raise HTTPException(status_code=400, detail="Question must contain 1–1500 characters.")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds the 20 MB upload limit.")
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    try:
        analysis = analyze_document(filename, content, enable_ocr=enable_ocr)
        return answer_question(question, analysis.clauses)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Unable to answer from document: {type(exc).__name__}") from exc
