const API_BASE = window.PDF_TO_MD_API_BASE || "http://localhost:8000";

const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const fileNameEl = document.getElementById("fileName");
const convertBtn = document.getElementById("convertBtn");
const pageHeadersToggle = document.getElementById("pageHeadersToggle");
const statusBar = document.getElementById("statusBar");
const resultSection = document.getElementById("resultSection");
const markdownSource = document.getElementById("markdownSource");
const markdownPreview = document.getElementById("markdownPreview");
const pageCountEl = document.getElementById("pageCount");
const copyBtn = document.getElementById("copyBtn");
const downloadBtn = document.getElementById("downloadBtn");

let selectedFile = null;
let currentMarkdown = "";
let currentFilename = "converted";

function setStatus(message, type) {
  if (!message) {
    statusBar.hidden = true;
    statusBar.textContent = "";
    return;
  }
  statusBar.hidden = false;
  statusBar.className = `status-bar ${type}`;
  if (type === "info") {
    statusBar.innerHTML = `<span class="spinner"></span>${message}`;
  } else {
    statusBar.textContent = message;
  }
}

function selectFile(file) {
  if (!file) return;
  const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
  if (!isPdf) {
    setStatus("Only PDF files are supported. Please choose a .pdf file.", "error");
    selectedFile = null;
    convertBtn.disabled = true;
    fileNameEl.textContent = "";
    return;
  }
  selectedFile = file;
  fileNameEl.textContent = file.name;
  convertBtn.disabled = false;
  setStatus("", null);
  resultSection.hidden = true;
}

dropzone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", (e) => selectFile(e.target.files[0]));

["dragenter", "dragover"].forEach((evt) => {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });
});

["dragleave", "drop"].forEach((evt) => {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
  });
});

dropzone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  selectFile(file);
});

convertBtn.addEventListener("click", async () => {
  if (!selectedFile) return;

  convertBtn.disabled = true;
  resultSection.hidden = true;
  setStatus("Converting your PDF to Markdown…", "info");

  const formData = new FormData();
  formData.append("file", selectedFile);
  formData.append("page_headers", pageHeadersToggle.checked);

  try {
    const response = await fetch(`${API_BASE}/api/convert`, {
      method: "POST",
      body: formData,
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.detail || "Something went wrong while converting the PDF.");
    }

    currentMarkdown = data.markdown;
    currentFilename = (selectedFile.name || "converted").replace(/\.pdf$/i, "");

    markdownSource.value = currentMarkdown;
    markdownPreview.innerHTML = window.marked
      ? window.marked.parse(currentMarkdown)
      : `<pre>${currentMarkdown}</pre>`;
    pageCountEl.textContent = `${data.pages} page${data.pages === 1 ? "" : "s"} converted`;

    resultSection.hidden = false;
    setStatus("Conversion complete.", "success");
  } catch (err) {
    setStatus(err.message, "error");
  } finally {
    convertBtn.disabled = false;
  }
});

copyBtn.addEventListener("click", async () => {
  if (!currentMarkdown) return;
  try {
    await navigator.clipboard.writeText(currentMarkdown);
    const original = copyBtn.textContent;
    copyBtn.textContent = "Copied!";
    setTimeout(() => (copyBtn.textContent = original), 1500);
  } catch {
    markdownSource.select();
    document.execCommand("copy");
  }
});

downloadBtn.addEventListener("click", () => {
  if (!currentMarkdown) return;
  const blob = new Blob([currentMarkdown], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${currentFilename}.md`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
});
