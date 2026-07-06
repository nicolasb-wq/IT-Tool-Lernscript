"""Lernscript-Generator — FastAPI-Webapp (MVP)."""
import io
import time
import uuid

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.services import claude_service, pdf_parser, quota
from app.services.pdf_generator import build_pdf

app = FastAPI(title="Lernscript-Generator")
templates = Jinja2Templates(directory="templates")

MAX_TOTAL_BYTES = 25 * 1024 * 1024

# Kurzlebiger In-Memory-Zwischenspeicher für generierte PDFs, da "einzelne Downloads
# nacheinander" mehrere separate HTTP-Requests braucht (eine Response = eine Datei).
# Jeder Eintrag wird nach dem ersten erfolgreichen Abruf sofort gelöscht — keine
# dauerhafte Speicherung, im Einklang mit der Datenschutz-Entscheidung des Projekts.
_RESULTS: dict[str, dict] = {}
_RESULT_TTL_SECONDS = 15 * 60


def _purge_expired_results() -> None:
    now = time.time()
    expired = [rid for rid, item in _RESULTS.items() if now - item["ts"] > _RESULT_TTL_SECONDS]
    for rid in expired:
        _RESULTS.pop(rid, None)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/generate")
async def generate(
    request: Request,
    files: list[UploadFile] = File(...),
    modulnummer: str = Form(""),
    user_api_key: str = Form(""),
):
    if not files:
        raise HTTPException(400, "Bitte mindestens eine PDF-Datei hochladen.")

    contents: list[tuple[str, bytes]] = []
    total_size = 0
    for f in files:
        if f.content_type != "application/pdf":
            raise HTTPException(400, f"'{f.filename}' ist keine PDF-Datei.")
        data = await f.read()
        total_size += len(data)
        contents.append((f.filename or "Datei.pdf", data))

    if total_size > MAX_TOTAL_BYTES:
        raise HTTPException(
            400,
            f"Gesamtgröße aller Dateien ({total_size / 1024 / 1024:.1f} MB) "
            f"überschreitet das Limit von 25 MB.",
        )

    # MVP-Nutzerkennung: Session-Cookie; später echtes Login (siehe ARCHITEKTUR.md)
    user_id = request.cookies.get("uid") or str(uuid.uuid4())
    own_key = user_api_key.strip() or None

    # Vorab-Check: Randfall-Entscheidung — ganzen Batch ablehnen, wenn das Freikontingent
    # nicht für alle hochgeladenen Dateien reicht (statt nur einen Teil zu verarbeiten).
    if not own_key:
        needed = len(contents)
        available = quota.remaining(user_id)
        if available < needed:
            raise HTTPException(
                402,
                f"Freikontingent reicht nicht aus: {needed} Datei(en) hochgeladen, "
                f"aber nur noch {available} freie Generierung(en) übrig. "
                f"Bitte eigenen API-Key angeben oder weniger Dateien hochladen.",
            )

    _purge_expired_results()
    results = []
    for filename, data in contents:
        try:
            api_key, used_free = quota.resolve_api_key(user_id, own_key)
        except ValueError as e:
            # Sollte dank Vorab-Check nicht auftreten, außer bei Nebenläufigkeit — sauber behandeln.
            raise HTTPException(402, str(e)) from e

        text = pdf_parser.extract_text(data)
        try:
            script = claude_service.generate_script(text, api_key, modulnummer or None)
        except Exception as e:
            raise HTTPException(502, f"KI-Generierung für '{filename}' fehlgeschlagen: {e}") from e

        if used_free:
            quota.consume(user_id)

        pdf_bytes = build_pdf(script)
        stem = filename.rsplit(".", 1)[0]
        out_name = f"Lernscript_{modulnummer or 'Modul'}_{stem}.pdf"
        result_id = str(uuid.uuid4())
        _RESULTS[result_id] = {"filename": out_name, "data": pdf_bytes, "ts": time.time()}
        results.append({"id": result_id, "filename": out_name})

    resp = JSONResponse({"results": results})
    resp.set_cookie("uid", user_id, max_age=60 * 60 * 24 * 365, httponly=True)
    return resp


@app.get("/download/{result_id}")
async def download(result_id: str):
    item = _RESULTS.pop(result_id, None)  # einmalig abrufbar, danach aus Speicher entfernt
    if not item:
        raise HTTPException(404, "Datei nicht gefunden oder bereits heruntergeladen.")
    return StreamingResponse(
        io.BytesIO(item["data"]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{item["filename"]}"'},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
