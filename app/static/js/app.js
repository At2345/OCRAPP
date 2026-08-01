const state = { file: null, result: null };

const $ = (id) => document.getElementById(id);
const dropzone = $("dropzone");
const fileInput = $("fileInput");
const uploadButton = $("uploadButton");

function setError(message) {
  const box = $("errorBox");
  box.textContent = message || "";
  box.classList.toggle("hidden", !message);
}

function setLoading(isLoading) {
  $("loading").classList.toggle("hidden", !isLoading);
  uploadButton.disabled = isLoading || !state.file;
}

function selectFile(file) {
  state.file = file;
  $("selectedFile").textContent = file ? `Selected: ${file.name}` : "";
  uploadButton.disabled = !file;
  setError(null);
}

function confidenceClass(score) {
  if (score >= 0.85) return ["text-emerald-300", "bg-emerald-400"];
  if (score >= 0.70) return ["text-amber-300", "bg-amber-400"];
  return ["text-rose-300", "bg-rose-400"];
}

function chip(label, item, color) {
  return `<span class="rounded-full border ${color} px-3 py-1">${label}: ${escapeHtml(item.value)} <span class="opacity-70">${Math.round(item.confidence_score * 100)}%</span></span>`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
}

function renderResult(result) {
  state.result = result;
  $("emptyState").classList.add("hidden");
  $("resultPanel").classList.remove("hidden");
  $("resultPanel").classList.add("fade-in");

  const reviewBanner = $("reviewBanner");
  reviewBanner.classList.toggle("hidden", !result.requires_human_review);
  $("reviewReasons").innerHTML = result.review_reasons.map((reason) => `<li>${escapeHtml(reason)}</li>`).join("");

  const duplicateBanner = $("duplicateBanner");
  duplicateBanner.classList.toggle("hidden", !result.is_duplicate);
  duplicateBanner.textContent = result.is_duplicate
    ? `Duplicate upload detected. Matches ${result.duplicate_of_filename || "a previous upload"}. Hash: ${result.file_hash.slice(0, 12)}...`
    : "";

  const [textClass, barClass] = confidenceClass(result.confidence_score);
  $("confidenceText").className = `mt-2 text-3xl font-bold ${textClass}`;
  $("confidenceText").textContent = `${Math.round(result.confidence_score * 100)}%`;
  $("confidenceBar").className = `confidence-bar h-full ${barClass}`;
  $("confidenceBar").style.width = `${Math.round(result.confidence_score * 100)}%`;
  $("pageCount").textContent = result.total_pages;
  $("statusText").className = `mt-2 text-2xl font-bold ${result.requires_human_review ? "text-amber-300" : "text-emerald-300"}`;
  $("statusText").textContent = result.requires_human_review ? "Flagged" : "Verified";

  const chips = [
    ...result.entities.emails.map((item) => chip("Email", item, "border-indigo-400/40 bg-indigo-500/10 text-indigo-200")),
    ...result.entities.phone_numbers.map((item) => chip("Phone", item, "border-emerald-400/40 bg-emerald-500/10 text-emerald-200")),
    ...result.entities.dates.map((item) => chip("Date", item, "border-sky-400/40 bg-sky-500/10 text-sky-200")),
  ];
  $("entityChips").innerHTML = chips.length ? chips.join("") : `<span class="text-slate-500">No dates, emails, or phone numbers detected.</span>`;
  $("fullText").value = result.full_text;
  $("pageDetails").innerHTML = result.pages.map((page) => `
    <details class="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
      <summary class="cursor-pointer font-medium">Page ${page.page_number} · ${Math.round(page.confidence_score * 100)}% confidence</summary>
      <pre class="mt-3 whitespace-pre-wrap text-sm text-slate-300">${escapeHtml(page.full_text)}</pre>
      ${page.unclear_segments.length ? `<p class="mt-3 text-sm text-amber-300">Unclear: ${escapeHtml(page.unclear_segments.join(", "))}</p>` : ""}
    </details>
  `).join("");
}

async function uploadFile() {
  if (!state.file) return;
  setLoading(true);
  setError(null);
  const formData = new FormData();
  formData.append("file", state.file);
  try {
    const response = await fetch("/api/digitize", { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || data.detail || "Upload failed.");
    renderResult(data);
  } catch (error) {
    setError(error.message);
  } finally {
    setLoading(false);
    fileInput.value = "";
  }
}

function download(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

async function downloadPdf() {
  if (!state.result) return;
  setError(null);
  const response = await fetch("/api/export/pdf", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      file_name: state.result.file_name || "digitized-document.pdf",
      title: state.result.file_name || "Digitized Document",
      text: $("fullText").value,
    }),
  });
  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.message || data.detail || "PDF export failed.");
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${(state.result.file_name || "digitized-document").replace(/\.[^.]+$/, "")}.pdf`;
  anchor.click();
  URL.revokeObjectURL(url);
}

dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("dragover", (event) => { event.preventDefault(); dropzone.classList.add("dragover"); });
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
dropzone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropzone.classList.remove("dragover");
  selectFile(event.dataTransfer.files[0]);
});
fileInput.addEventListener("change", (event) => selectFile(event.target.files[0]));
uploadButton.addEventListener("click", uploadFile);
$("copyButton").addEventListener("click", () => navigator.clipboard.writeText($("fullText").value));
$("downloadTextButton").addEventListener("click", () => download("ocr-transcript.txt", $("fullText").value, "text/plain"));
$("downloadPdfButton").addEventListener("click", () => downloadPdf().catch((error) => setError(error.message)));
$("downloadJsonButton").addEventListener("click", () => download("ocr-result.json", JSON.stringify(state.result, null, 2), "application/json"));
