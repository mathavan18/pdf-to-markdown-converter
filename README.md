# PDF to Markdown Converter

A single-page web app that converts a text-based PDF into clean Markdown —
preserving page breaks (`## Page N`) and rendering detected tables as
Markdown tables. Files are processed in memory only; nothing is persisted.

## Project layout

```
.
├── backend/           FastAPI app (pdfplumber-based extraction)
│   ├── main.py
│   ├── converter.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/           Plain HTML/JS/CSS UI (no build step)
│   ├── index.html
│   ├── app.js
│   ├── config.js       backend API URL, overwritten at deploy time
│   └── style.css
├── render.yaml          Render blueprint for the backend
└── .github/workflows/deploy-pages.yml   deploys frontend/ to GitHub Pages
```

## Run the backend

```bash
cd backend
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
cd frontend
python -m http.server 5500
```

Then open `http://localhost:5500` in your browser.

By default the frontend calls the backend at `http://localhost:8000` (see
`frontend/config.js`). To point it elsewhere for local testing, edit that
file or set `window.PDF_TO_MD_API_BASE` before `app.js` loads.

## Deploy to the internet

**Backend → Render:**

1. In the [Render dashboard](https://dashboard.render.com), click **New +** →
   **Blueprint**, connect this GitHub repo. Render detects `render.yaml` and
   creates a free web service (`pdf-to-markdown-backend`) automatically.
2. Deploy and copy the resulting URL, e.g.
   `https://pdf-to-markdown-backend.onrender.com`.
   (Free-tier services spin down after inactivity — the first request after
   idling can take ~30-50s to wake up.)

**Frontend → GitHub Pages:**

1. In this repo, go to **Settings → Pages → Build and deployment → Source**
   and select **GitHub Actions**.
2. Go to **Settings → Secrets and variables → Actions → Variables** and add
   a repository variable `API_BASE_URL` set to your Render backend URL from
   above (no trailing slash).
3. Push to `main` (or run the **Deploy frontend to GitHub Pages** workflow
   manually from the **Actions** tab). The workflow injects `API_BASE_URL`
   into `config.js` at build time and publishes `frontend/` to Pages.
4. Your app will be live at
   `https://<your-github-username>.github.io/pdf-to-markdown-converter/`.

Re-running step 3 (any push to `main` touching `frontend/`) redeploys with
the current `API_BASE_URL` value.

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
