import asyncio

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from converter import ScannedPDFError, convert_pdf_to_markdown

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB

app = FastAPI(title="PDF to Markdown Converter")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/convert")
async def convert(file: UploadFile = File(...), page_headers: bool = Form(True)):
    is_pdf_type = file.content_type in ("application/pdf", "application/x-pdf")
    is_pdf_name = (file.filename or "").lower().endswith(".pdf")
    if not (is_pdf_type or is_pdf_name):
        raise HTTPException(status_code=400, detail="Only PDF files are supported. Please upload a .pdf file.")

    content = await file.read()

    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="This file doesn't look like a valid PDF.")

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File is too large. Please upload a PDF under 25 MB.")

    try:
        # Run the CPU-bound extraction in a worker thread so large, multi-page
        # PDFs don't block the event loop or trip a request timeout.
        markdown, page_count = await asyncio.to_thread(convert_pdf_to_markdown, content, page_headers)
    except ScannedPDFError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"markdown": markdown, "pages": page_count, "filename": file.filename}
