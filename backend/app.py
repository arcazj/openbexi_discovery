"""Run: python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000."""

# IntelliJ's Run action executes this file directly, including from backend/.
# Delegate before relative imports so Run and Debug load the same application.
if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from run_discovery import main
    main()
    raise SystemExit(0)

import asyncio
import ipaddress
import os
import re
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Literal, Optional

import httpx
from dotenv import load_dotenv, set_key
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator
from pydantic import ValidationError
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import ai
from .discovery_api import router as discovery_router, tracked_ai
from .discovery_store import require_online, data_root, LOCK
from .sources import SOURCE_INFO, SourceService, interpret, utc_now

ROOT = Path(__file__).resolve().parent.parent


def configuration_path():
    # The installed app keeps credentials separate from bundled files/upgrades.
    directory = (os.getenv("DISCOVERY_DATA_DIR") or os.getenv("REI_DATA_DIR", "")).strip()
    return (Path(directory).resolve() if directory else ROOT) / ".env"


load_dotenv(configuration_path(), override=False)
VERSION = "1.2.0"
# The standalone launcher can select any free local port. Keep browser access
# limited to exact loopback HTTP origins, using one policy for CORS and POSTs.
LOCAL_PORT_PATTERN = r"(?:[1-9][0-9]{0,3}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])"
LOCAL_ORIGIN_PATTERN = rf"http://(?:localhost|127\.0\.0\.1)(?::{LOCAL_PORT_PATTERN})?"
LOCAL_ORIGIN = re.compile(LOCAL_ORIGIN_PATTERN)
DOC_FILES = {"README.md", "CHANGELOG.md", "RELEASE-NOTES-v1.2.0.md", "WINDOWS_INSTALLATION.md", "HELP.md", "COMMERCIAL_LICENSING.md", "THIRD_PARTY_NOTICES.md", "REI_RESEARCH_EXPLORER_PROMPT.md", "LICENSE"}


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=250)
    mode: Literal["auto", "topic", "gene", "region"] = "auto"
    sources: List[Literal["pubmed", "ensembl", "gwas"]] = Field(default_factory=lambda: ["pubmed", "ensembl", "gwas"], min_length=1, max_length=3)
    limit: int = Field(default=10, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def valid_query(cls, value: str) -> str:
        if not value.strip() or any(ord(ch) < 32 for ch in value):
            raise ValueError("Enter a nonempty query without control characters.")
        return value.strip()

    @field_validator("sources")
    @classmethod
    def unique_sources(cls, value: List[str]) -> List[str]:
        if len(set(value)) != len(value):
            raise ValueError("Select each source only once.")
        return value


class AIConfigureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    api_key: Optional[SecretStr] = Field(default=None, min_length=20, max_length=512)
    model: Optional[str] = Field(default=None, min_length=1, max_length=100)
    reasoning_effort: Optional[Literal["low", "medium", "high", "xhigh", "max"]] = None

    @field_validator("api_key", mode="before")
    @classmethod
    def trim_key(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("api_key")
    @classmethod
    def valid_key(cls, value: Optional[SecretStr]) -> Optional[SecretStr]:
        if value is not None and re.fullmatch(r"sk-[A-Za-z0-9_-]+", value.get_secret_value()) is None:
            raise ValueError("Enter a complete OpenAI secret key beginning with sk-.")
        return value

    @field_validator("model")
    @classmethod
    def supported_model(cls, value):
        if value is not None and value not in ai.MODELS and value != ai.model_name():
            raise ValueError("Choose one of the supported AI models.")
        return value

    @model_validator(mode="after")
    def has_change(self):
        if self.api_key is None and self.model is None and self.reasoning_effort is None:
            raise ValueError("Choose a model, reasoning level, or API key to save.")
        return self


@asynccontextmanager
async def lifespan(application: FastAPI):
    async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=8.0, pool=8.0), follow_redirects=False,
                                 headers={"User-Agent": "REIResearchExplorer/1.0 (local fellowship research workspace)"},
                                 limits=httpx.Limits(max_connections=12, max_keepalive_connections=6)) as client:
        application.state.sources = SourceService(client, os.getenv("NCBI_EMAIL", ""))
        application.state.search_slots = asyncio.Semaphore(6)
        application.state.ai_slots = asyncio.Semaphore(2)
        yield


app = FastAPI(title="OpenBEXI Discovery", version=VERSION, lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"])
app.add_middleware(CORSMiddleware, allow_origin_regex=LOCAL_ORIGIN_PATTERN, allow_methods=["GET", "POST"],
                   allow_headers=["Content-Type"], expose_headers=["X-Discovery-AI-Reused"], allow_credentials=False)


@app.middleware("http")
async def request_limits(request: Request, call_next):
    if request.method == "POST":
        if request.url.path.startswith("/api/discovery/"):
            try:
                local_peer = request.client is not None and ipaddress.ip_address(request.client.host).is_loopback
            except ValueError:
                local_peer = False
            if not local_peer:
                return JSONResponse({"detail": "Discovery data can only be changed from this computer."}, status_code=403)
        origin = request.headers.get("origin")
        if origin is not None and LOCAL_ORIGIN.fullmatch(origin) is None:
            return JSONResponse({"detail": "Serve index.html over local HTTP with serve_frontend.py, then connect to the Python backend in Help. File URLs and nonlocal web origins cannot use this API."}, status_code=403)
        if "application/json" not in request.headers.get("content-type", "").lower():
            return JSONResponse({"detail": "API requests must use application/json."}, status_code=415)
        try:
            declared_length = int(request.headers.get("content-length", "0"))
        except ValueError:
            return JSONResponse({"detail": "Invalid request length."}, status_code=400)
        maximum = 46_000_000 if request.url.path.startswith("/api/discovery/") else 120000
        if declared_length > maximum:
            return JSONResponse({"detail": "Request too large. Select fewer evidence records."}, status_code=413)
        chunks, size = [], 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > maximum:
                return JSONResponse({"detail": "Request too large. Select a smaller file or request."}, status_code=413)
            chunks.append(chunk)
        request._body = b"".join(chunks)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    # Do not echo input values, which may contain accidentally pasted credentials.
    errors = [{"field": ".".join(str(v) for v in e["loc"]), "message": e["msg"]} for e in exc.errors()]
    return JSONResponse({"detail": "Check the request fields.", "errors": errors}, status_code=422)


@app.exception_handler(ValidationError)
async def schema_error(request: Request, exc: ValidationError):
    return JSONResponse({"detail": "Content does not match the supported schema.",
                         "errors": [{"field": ".".join(str(v) for v in e["loc"]), "message": e["msg"]} for e in exc.errors()]}, status_code=422)


app.include_router(discovery_router)


@app.get("/api/health")
async def health():
    result = {"version": VERSION, "ai": {"configured": ai.configured(), "model": ai.model_name(),
              "reasoning_effort": ai.reasoning_effort()}, "sources": SOURCE_INFO}
    if os.getenv("REI_DESKTOP_INSTANCE"):
        result["desktop"] = {"managed": True, "instance_id": os.environ["REI_DESKTOP_INSTANCE"]}
    return result


@app.post("/api/search")
async def search(request: SearchRequest):
    require_online()
    try:
        interpretation = interpret(request.query, request.mode)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    async with app.state.search_slots:
        responses = await asyncio.gather(*(app.state.sources.search(source, interpretation, request.limit) for source in request.sources))
    return {"query": request.query, "interpretation": interpretation,
            "records": [record for result in responses for record in result["records"]],
            "coverage": [result["coverage"] for result in responses], "retrieved_at": utc_now(), "demo": False}


@app.post("/api/ai")
async def ai_request(request: ai.AIRequest):
    async with app.state.ai_slots:
        return await tracked_ai(ai.generate(request))


@app.post("/api/ai/check")
@app.get("/api/ai/check")
async def ai_check():
    return await ai.check_connection()


@app.post("/api/ai/configure")
async def ai_configure(configuration: AIConfigureRequest, request: Request):
    # A local-looking Origin or Host is not proof that the network peer is local.
    # Never trust X-Forwarded-For here: this endpoint changes server credentials.
    try:
        local_client = request.client is not None and ipaddress.ip_address(request.client.host).is_loopback
    except ValueError:
        local_client = False
    if not local_client:
        raise HTTPException(403, "AI settings can only be configured from this computer.")
    updates = {}
    if configuration.api_key is not None:
        updates["OPENAI_API_KEY"] = configuration.api_key.get_secret_value()
    if configuration.model is not None:
        updates["OPENAI_MODEL"] = configuration.model
    if configuration.reasoning_effort is not None:
        updates["OPENAI_REASONING_EFFORT"] = configuration.reasoning_effort
    # Save the complete change atomically before updating the running process.
    # Omitted keys remain private and unchanged when only preferences are saved.
    with LOCK:
        temporary = None
        try:
            path = configuration_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(prefix=".env-", dir=path.parent)
            os.close(fd)
            temporary = Path(name)
            if path.exists():
                temporary.write_bytes(path.read_bytes())
            for setting, value in updates.items():
                if not set_key(str(temporary), setting, value, quote_mode="always")[0]:
                    raise OSError("Settings write failed")
            temporary.replace(path)
        except Exception:
            raise HTTPException(500, "Could not save AI settings. Check that the private settings folder and .env are writable, then try again.") from None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        os.environ.update(updates)
    return {"configured": ai.configured(), "model": ai.model_name(), "reasoning_effort": ai.reasoning_effort(),
            "accessible": False, "message": "AI settings saved on this computer. Check AI access to verify the connection."}


@app.get("/")
@app.get("/index.html")
async def frontend():
    path = ROOT / "index.html"
    if not path.is_file():
        raise HTTPException(404, "Frontend is not installed.")
    return FileResponse(path, media_type="text/html")


@app.get("/api/docs/{filename}")
async def docs(filename: str):
    if filename not in DOC_FILES or not (ROOT / filename).is_file():
        raise HTTPException(404, "Documentation not found.")
    return FileResponse(ROOT / filename, media_type="text/markdown; charset=utf-8")


@app.get("/licenses/{filename}")
async def license_file(filename: str):
    directory = ROOT / "licenses"
    path = (directory / filename).resolve()
    if path.parent != directory.resolve() or not filename.endswith(".txt") or not path.is_file():
        raise HTTPException(404, "License text not found.")
    return FileResponse(path, media_type="text/plain; charset=utf-8")


@app.get("/assets/{filename}")
async def discovery_asset(filename: str):
    if filename not in {"discovery.js", "discovery.css", "data.js", "captions.js", "customize.js", "profile_ai.js", "ai_progress.js"}:
        raise HTTPException(404, "Asset not found.")
    return FileResponse(ROOT / "assets" / filename)


@app.get("/documentation/{filename}")
async def discovery_document(filename: str):
    path = ROOT / "documentation" / filename
    if not filename.endswith(".md") or path.is_symlink() or not path.is_file():
        raise HTTPException(404, "Document not found.")
    return FileResponse(path, media_type="text/plain; charset=utf-8")


@app.get("/{filename}")
async def document_link(filename: str):
    # Relative documentation links resolve without exposing the project directory.
    return await docs(filename)
