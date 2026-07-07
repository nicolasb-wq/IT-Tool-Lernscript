"""Lernscript-Generator — FastAPI-Webapp mit Login (MVP)."""
import io
import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.db import get_session, init_db
from app.models import User
from app.services import claude_service, pdf_parser, quota
from app.services.auth import AuthError, authenticate, register_user
from app.services.pdf_generator import build_pdf
from app.services.pdf_parser import ParserError


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Lernscript-Generator", lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "dev-only-insecure-change-me"),
    https_only=os.getenv("SESSION_HTTPS_ONLY", "0") == "1",
)
templates = Jinja2Templates(directory="templates")

MAX_TOTAL_BYTES = 25 * 1024 * 1024

# Kurzlebiger In-Memory-Zwischenspeicher für generierte PDFs (Einzeldownloads).
# Einträge werden nach erstem Abruf oder 15 Min. TTL entfernt — keine Persistenz.
_RESULTS: dict[str, dict] = {}
_RESULT_TTL_SECONDS = 15 * 60


def _purge_expired_results() -> None:
    now = time.time()
    for rid in [r for r, item in _RESULTS.items() if now - item["ts"] > _RESULT_TTL_SECONDS]:
        _RESULTS.pop(rid, None)


def _current_user_id(request: Request) -> int | None:
    return request.session.get("user_id")


# ------------------------------------------------------------------ Auth-Seiten
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.get("/impressum", response_class=HTMLResponse)
async def impressum_page(request: Request):
    return templates.TemplateResponse(request, "impressum.html", {})


@app.get("/datenschutz", response_class=HTMLResponse)
async def datenschutz_page(request: Request):
    return templates.TemplateResponse(request, "datenschutz.html", {})


@app.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    db = get_session()
    try:
        user = authenticate(db, email, password)
    except AuthError as e:
        return templates.TemplateResponse(
            request, "login.html", {"error": str(e)}, status_code=401
        )
    finally:
        db.close()
    request.session["user_id"] = user.id
    return RedirectResponse("/", status_code=303)


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {"error": None})


@app.post("/register", response_class=HTMLResponse)
async def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    invite_code: str = Form(...),
):
    db = get_session()
    try:
        user = register_user(db, email, password, invite_code)
    except AuthError as e:
        return templates.TemplateResponse(
            request, "register.html", {"error": str(e)}, status_code=400
        )
    finally:
        db.close()
    request.session["user_id"] = user.id
    return RedirectResponse("/", status_code=303)


@app.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


# ------------------------------------------------------------------ App-Seiten
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user_id = _current_user_id(request)
    if user_id is None:
        return RedirectResponse("/login", status_code=303)
    db = get_session()
    try:
        user = db.get(User, user_id)
        if user is None:
            request.session.clear()
            return RedirectResponse("/login", status_code=303)
        free_left = quota.remaining(db, user_id)
    finally:
        db.close()
    return templates.TemplateResponse(
        request, "index.html", {"email": user.email, "free_left": free_left}
    )


@app.post("/generate")
async def generate(
    request: Request,
    files: list[UploadFile] = File(...),
    modulnummer: str = Form(""),
    user_api_key: str = Form(""),
):
    user_id = _current_user_id(request)
    if user_id is None:
        raise HTTPException(401, "Bitte zuerst einloggen.")

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

    own_key = user_api_key.strip() or None
    db = get_session()
    try:
        # Randfall-Entscheidung: ganzen Batch ablehnen, wenn das Freikontingent
        # nicht für ALLE Dateien reicht (kein Teilverarbeiten).
        if not own_key:
            needed, available = len(contents), quota.remaining(db, user_id)
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
                api_key, used_free = quota.resolve_api_key(db, user_id, own_key)
            except ValueError as e:
                raise HTTPException(402, str(e)) from e

            try:
                text = pdf_parser.extract_text(data)
            except ParserError as e:
                raise HTTPException(400, f"'{filename}': {e}") from e
            try:
                script = claude_service.generate_script(text, api_key, modulnummer or None)
            except Exception as e:
                raise HTTPException(
                    502, f"KI-Generierung für '{filename}' fehlgeschlagen: {e}"
                ) from e

            if used_free:
                quota.consume(db, user_id)

            pdf_bytes = build_pdf(script)
            stem = filename.rsplit(".", 1)[0]
            out_name = f"Lernscript_{modulnummer or 'Modul'}_{stem}.pdf"
            result_id = str(uuid.uuid4())
            _RESULTS[result_id] = {
                "filename": out_name, "data": pdf_bytes, "ts": time.time(), "user_id": user_id,
            }
            results.append({"id": result_id, "filename": out_name})
    finally:
        db.close()

    return JSONResponse({"results": results})


@app.get("/download/{result_id}")
async def download(request: Request, result_id: str):
    user_id = _current_user_id(request)
    if user_id is None:
        raise HTTPException(401, "Bitte zuerst einloggen.")
    _purge_expired_results()
    item = _RESULTS.get(result_id)
    if not item or item["user_id"] != user_id:
        raise HTTPException(404, "Datei nicht gefunden oder bereits heruntergeladen.")
    _RESULTS.pop(result_id, None)  # einmalig abrufbar
    return StreamingResponse(
        io.BytesIO(item["data"]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{item["filename"]}"'},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
