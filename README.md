# PDF to Markdown Converter

A single-page web app that converts a text-based PDF into clean Markdown —
preserving page breaks (`## Page N`) and rendering detected tables as
Markdown tables. Files are processed in memory only; nothing is persisted.

## Project layout

```
pdf-to-markdown/
├── backend/          FastAPI app (pdfplumber-based extraction)
│   ├── main.py
│   ├── converter.py
│   └── requirements.txt
└── frontend/          Plain HTML/JS/CSS UI (no build step)
    ├── index.html
    ├── app.js
    └── style.css
```

## Run the backend

```bash
cd pdf-to-markdown/backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The API is now available at `http://localhost:8000`, with the conversion
endpoint at `POST /api/convert` (multipart form field `file`, optional
`page_headers` boolean).

## Run the frontend

No build tooling or `npm install` required — it's static HTML/JS. Serve it
with any static file server, for example:

```bash
cd pdf-to-markdown/frontend
python -m http.server 5500
```

Then open `http://localhost:5500` in your browser.

By default the frontend calls the backend at `http://localhost:8000`. To
point it elsewhere, set `window.PDF_TO_MD_API_BASE` before `app.js` loads,
e.g. add this in `index.html`:

```html
<script>window.PDF_TO_MD_API_BASE = "https://your-backend-host";</script>
```

## How it works

- The backend uses `pdfplumber` to walk each page, locate tables via
  `page.find_tables()`, and extract the remaining text lines with the table
  regions excluded (`page.outside_bbox()`).
- Text lines and tables are merged back together in their original vertical
  order, so a table appears in the Markdown roughly where it appeared on
  the page.
- Excessive whitespace is collapsed (repeated spaces, 3+ blank lines) while
  paragraph breaks are preserved.
- If no page yields any extractable text, the API returns a 422 with a
  message explaining the PDF looks scanned/image-only and that OCR isn't
  supported.
- Conversion runs in a worker thread (`asyncio.to_thread`) so large,
  multi-page PDFs don't block the server or trip a request timeout.

## Edge cases handled

- Non-PDF uploads are rejected with a clear error (checked by both
  extension/content-type and the `%PDF-` file signature).
- Scanned/image-only PDFs return a friendly message instead of empty output.
- Files over 25 MB are rejected with a 413 response.
- Multi-page PDFs (10+ pages) are supported; extraction runs off the main
  event loop.

## Nice-to-haves included

- Toggle to turn `## Page N` headings on/off before converting.
- Copy-to-clipboard button for the generated Markdown.
- Drag-and-drop upload with a visual drop zone (plus a regular file picker).
- Live side-by-side preview: raw Markdown source and rendered HTML preview.
