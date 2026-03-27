from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
import os
import sys
from typing import Literal

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

try:
    from services.nlp_engine import NLPEngine
    from services.agentic_engine import AgenticEngine
except ImportError:
    from .services.nlp_engine import NLPEngine
    from .services.agentic_engine import AgenticEngine

app = FastAPI(title="Twitter Analytics API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = NLPEngine()
agentic_engine = AgenticEngine(engine)


def _normalize_url(value: str) -> str:
    url = (value or "").strip()
    if not url:
        return ""
    url = url.replace("http://", "https://")
    url = url.replace("twitter.com/", "x.com/")
    url = url.replace("www.x.com/", "x.com/")
    url = url.split("?", 1)[0].rstrip("/")
    return url.lower()


def _extract_status_url_parts(url: str) -> tuple[str, str]:
    raw = (url or "").strip()
    match = re.search(r"(?:https?://)?(?:www\.)?(?:x|twitter)\.com/([^/]+)/status/([^/?#]+)", raw, flags=re.IGNORECASE)
    if not match:
        return "", ""
    handle = (match.group(1) or "").strip().lstrip("@").lower()
    status_id = (match.group(2) or "").strip()
    return handle, status_id


def _is_placeholder_status_id(status_id: str) -> bool:
    sid = (status_id or "").strip().lower()
    if not sid:
        return True
    if sid.isdigit():
        return False
    if "simulated" in sid or "{" in sid or "}" in sid:
        return True
    return True


class AnalyzeRequest(BaseModel):
    mode: Literal["text", "url", "handle", "rows", "dataset"] = "url"
    texts: list[str] = Field(default_factory=list)
    urls: list[str] = Field(default_factory=list)
    rows: list[dict] = Field(default_factory=list)
    handle: str = ""
    count: int = Field(default=10, ge=1, le=50)


class AgentRequest(BaseModel):
    question: str = Field(min_length=2)
    context: list[dict] = Field(default_factory=list)


class AgenticRequest(BaseModel):
    question: str = Field(min_length=2)
    context: list[dict] = Field(default_factory=list)


# ========== FRONTEND SERVING ==========
# Get the root directory (where backend folder is)
ROOT_DIR = Path(__file__).parent.parent
FRONTEND_BUILD_DIR = ROOT_DIR / "frontend" / "dist"
FRONTEND_SOURCE_DIR = ROOT_DIR / "frontend"

# Try to serve built frontend first
if FRONTEND_BUILD_DIR.exists() and (FRONTEND_BUILD_DIR / "index.html").exists():
    print(f"Serving frontend from: {FRONTEND_BUILD_DIR}")
    
    # Mount static assets
    assets_path = FRONTEND_BUILD_DIR / "assets"
    if assets_path.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")
    
    @app.get("/")
    async def serve_frontend_build():
        return FileResponse(str(FRONTEND_BUILD_DIR / "index.html"))
    
    # Handle SPA routing - all non-API routes go to index.html
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Skip API and documentation routes
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("redoc") or full_path.startswith("openapi.json"):
            raise HTTPException(status_code=404, detail="Not found")
        
        # Check if it's a static file
        file_path = FRONTEND_BUILD_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        
        # Return index.html for SPA routing
        return FileResponse(str(FRONTEND_BUILD_DIR / "index.html"))

elif FRONTEND_SOURCE_DIR.exists() and (FRONTEND_SOURCE_DIR / "index.html").exists():
    print(f"Serving frontend source from: {FRONTEND_SOURCE_DIR} (development mode)")
    
    @app.get("/")
    async def serve_frontend_dev():
        return FileResponse(str(FRONTEND_SOURCE_DIR / "index.html"))
    
    @app.get("/{full_path:path}")
    async def serve_spa_dev(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("redoc"):
            raise HTTPException(status_code=404, detail="Not found")
        
        file_path = FRONTEND_SOURCE_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        
        return FileResponse(str(FRONTEND_SOURCE_DIR / "index.html"))

else:
    print("No frontend found. API only mode.")
    @app.get("/")
    async def api_info():
        return {
            "message": "Twitter Analytics API is running",
            "version": "1.0.0",
            "status": "online",
            "docs": "/docs",
            "note": "Frontend not found. Please build frontend first: cd frontend && npm install && npm run build"
        }


# ========== API ENDPOINTS ==========
@app.get("/api")
def api_root() -> dict:
    """API information endpoint"""
    return {
        "message": "Twitter Analytics API is running",
        "version": "1.0.0",
        "endpoints": {
            "GET /api": "This information",
            "GET /api/health": "Health check",
            "GET /docs": "Swagger UI documentation",
            "GET /redoc": "ReDoc documentation",
            "POST /api/analyze": "Analyze tweets (text, URLs, handle, rows, dataset)",
            "POST /api/agent": "Simple agent question answering",
            "POST /api/agentic": "Advanced agentic workflow",
            "POST /api/analyze-file": "Upload and analyze CSV/Excel file",
            "POST /api/analyze-download": "Analyze latest Twitter analysis file from Downloads"
        },
        "documentation": "/docs",
        "status": "online"
    }


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/analyze")
def analyze(payload: AnalyzeRequest) -> dict:
    download_records = _get_download_records()

    if payload.mode == "text":
        clean_texts = [text.strip() for text in payload.texts if text.strip()]
        analyzed = engine.analyze_texts(clean_texts)
    elif payload.mode == "dataset":
        analyzed = engine.analyze_project_dataset(payload.count, payload.handle.strip())
    elif payload.mode == "rows":
        analyzed = engine.analyze_rows(payload.rows, payload.count)
    elif payload.mode == "handle":
        analyzed = engine.analyze_handle(payload.handle.strip(), payload.count)
        if download_records:
            filtered = _filter_records_by_handle(download_records, payload.handle.strip())
            sheet_rows = engine.analyze_rows(filtered, payload.count)
            if not analyzed:
                analyzed = sheet_rows
            elif len(analyzed) < payload.count and sheet_rows:
                seen = {_normalize_url(str(row.get("source_url", ""))) for row in analyzed}
                for row in sheet_rows:
                    key = _normalize_url(str(row.get("source_url", "")))
                    if key and key in seen:
                        continue
                    analyzed.append(row)
                    if key:
                        seen.add(key)
                    if len(analyzed) >= payload.count:
                        break
    else:
        clean_urls = [url.strip() for url in payload.urls if url.strip()][: payload.count]
        matched_records, unresolved_urls = _match_records_by_urls(download_records, clean_urls)
        if matched_records and len(matched_records) < payload.count:
            matched_records = _expand_records_by_user(download_records, matched_records, payload.count)
        analyzed = engine.analyze_rows(matched_records, payload.count) if matched_records else []
        if unresolved_urls and len(analyzed) < payload.count:
            remaining = payload.count - len(analyzed)
            direct_urls: list[str] = []
            handle_fallbacks: list[str] = []
            for url in unresolved_urls:
                handle, status_id = _extract_status_url_parts(url)
                if handle and _is_placeholder_status_id(status_id):
                    handle_fallbacks.append(handle)
                else:
                    direct_urls.append(url)
                    if handle:
                        handle_fallbacks.append(handle)

            if direct_urls and remaining > 0:
                live_rows = engine.analyze_urls(direct_urls[:remaining])
                analyzed.extend(live_rows)
                remaining = payload.count - len(analyzed)

            if handle_fallbacks and remaining > 0:
                seen_handles: set[str] = set()
                seen_urls = {_normalize_url(str(row.get("source_url", ""))) for row in analyzed}
                for handle in handle_fallbacks:
                    if handle in seen_handles:
                        continue
                    seen_handles.add(handle)

                    merged_rows: list[dict] = []
                    filtered = _filter_records_by_handle(download_records, handle)
                    if filtered:
                        merged_rows.extend(engine.analyze_rows(filtered, remaining))

                    if len(merged_rows) < remaining:
                        live_rows = engine.analyze_handle(handle, remaining)
                        merged_rows.extend(live_rows)

                    if not merged_rows:
                        continue

                    for row in merged_rows:
                        key = _normalize_url(str(row.get("source_url", "")))
                        if key and key in seen_urls:
                            continue
                        analyzed.append(row)
                        if key:
                            seen_urls.add(key)
                        if len(analyzed) >= payload.count:
                            break
                    remaining = payload.count - len(analyzed)
                    if remaining <= 0:
                        break

        if len(analyzed) < payload.count:
            remaining = payload.count - len(analyzed)
            seen_handles: set[str] = set()
            seen_urls = {_normalize_url(str(row.get("source_url", ""))) for row in analyzed}
            for url in clean_urls:
                handle, _ = _extract_status_url_parts(url)
                if not handle or handle in seen_handles:
                    continue
                seen_handles.add(handle)

                merged_rows: list[dict] = []
                filtered = _filter_records_by_handle(download_records, handle)
                if filtered:
                    merged_rows.extend(engine.analyze_rows(filtered, remaining))

                if len(merged_rows) < remaining:
                    merged_rows.extend(engine.analyze_handle(handle, remaining))

                for row in merged_rows:
                    key = _normalize_url(str(row.get("source_url", "")))
                    if key and key in seen_urls:
                        continue
                    analyzed.append(row)
                    if key:
                        seen_urls.add(key)
                    if len(analyzed) >= payload.count:
                        break
                remaining = payload.count - len(analyzed)
                if remaining <= 0:
                    break

    summary = engine.aggregate(analyzed)
    trends = engine.build_trends(analyzed)
    return {"summary": summary, "rows": analyzed, "trends": trends}


@app.post("/api/agent")
def agent(payload: AgentRequest) -> dict:
    answer = engine.agent_answer(payload.question, payload.context)
    summary = engine.aggregate(payload.context)
    return {"answer": answer, "summary": summary}


@app.post("/api/agentic")
def agentic(payload: AgenticRequest) -> dict:
    summary = engine.aggregate(payload.context)
    execution = agentic_engine.run(payload.question, payload.context)
    return {
        "answer": execution.get("answer", ""),
        "summary": summary,
        "plan": execution.get("plan", []),
        "steps": execution.get("steps", []),
        "confidence": execution.get("confidence", "low"),
        "tools": execution.get("tools", []),
    }


def _read_table_by_suffix(path: Path) -> pd.DataFrame:
    name = path.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(path)
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(path)
    raise ValueError("Unsupported file type")


def _find_latest_download_dataset() -> Path | None:
    downloads_dir = Path.home() / "Downloads"
    if not downloads_dir.exists():
        return None

    patterns = [
        "*twitter*analysis*.xlsx",
        "*twitter*analysis*.xls",
        "*twitter*analysis*.csv",
        "*twitter*analyse*data*.xlsx",
        "*twitter*analyse*data*.xls",
        "*twitter*analyse*data*.csv",
        "*twitter*.xlsx",
        "*twitter*.xls",
        "*twitter*.csv",
        "*tweet*.xlsx",
        "*tweet*.xls",
        "*tweet*.csv",
    ]

    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(downloads_dir.glob(pattern))

    files = [item for item in candidates if item.is_file() and not item.name.startswith("~$")]
    if not files:
        return None
    return max(files, key=lambda item: item.stat().st_mtime)


def _get_download_records() -> list[dict]:
    download_file = _find_latest_download_dataset()
    if not download_file:
        return []
    try:
        frame = _read_table_by_suffix(download_file)
        return frame.fillna("").to_dict(orient="records")
    except Exception:
        return []


def _filter_records_by_handle(records: list[dict], handle: str) -> list[dict]:
    wanted = handle.strip().lstrip("@").lower()
    if not wanted:
        return records
    filtered: list[dict] = []
    for row in records:
        value = str(row.get("user") or row.get("author.userName") or row.get("username") or "").strip().lstrip("@").lower()
        if value == wanted:
            filtered.append(row)
    return filtered


def _match_records_by_urls(records: list[dict], urls: list[str]) -> tuple[list[dict], list[str]]:
    index: dict[str, dict] = {}
    for row in records:
        candidates = [
            str(row.get("url") or ""),
            str(row.get("twitterUrl") or ""),
            str(row.get("source_url") or ""),
        ]
        for value in candidates:
            key = _normalize_url(value)
            if key:
                index[key] = row

    matched: list[dict] = []
    unresolved: list[str] = []
    for url in urls:
        key = _normalize_url(url)
        row = index.get(key)
        if row:
            matched.append(row)
        else:
            unresolved.append(url)
    return matched, unresolved


def _expand_records_by_user(records: list[dict], seeds: list[dict], limit: int) -> list[dict]:
    if not records or not seeds or limit <= len(seeds):
        return seeds[:limit]

    expanded: list[dict] = list(seeds)
    seen_urls = {_normalize_url(str(item.get("url") or item.get("twitterUrl") or item.get("source_url") or "")) for item in expanded}
    seed_users = {
        str(item.get("user") or item.get("author.userName") or item.get("username") or "").strip().lstrip("@").lower()
        for item in seeds
    }
    seed_users.discard("")

    for row in records:
        if len(expanded) >= limit:
            break
        user_key = str(row.get("user") or row.get("author.userName") or row.get("username") or "").strip().lstrip("@").lower()
        if seed_users and user_key not in seed_users:
            continue
        row_key = _normalize_url(str(row.get("url") or row.get("twitterUrl") or row.get("source_url") or ""))
        if row_key and row_key in seen_urls:
            continue
        expanded.append(row)
        if row_key:
            seen_urls.add(row_key)

    return expanded[:limit]


@app.post("/api/analyze-file")
async def analyze_file(file: UploadFile = File(...), count: int = Form(10)) -> dict:
    safe_count = max(1, min(int(count), 50))
    file_name = (file.filename or "").lower()
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        if file_name.endswith(".csv"):
            frame = pd.read_csv(BytesIO(content))
        elif file_name.endswith(".xlsx") or file_name.endswith(".xls"):
            frame = pd.read_excel(BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Please upload a .csv, .xlsx, or .xls file.")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to parse file: {exc}")

    records = frame.fillna("").to_dict(orient="records")
    analyzed = engine.analyze_rows(records, safe_count)
    summary = engine.aggregate(analyzed)
    trends = engine.build_trends(analyzed)
    return {"summary": summary, "rows": analyzed, "trends": trends}


@app.post("/api/analyze-download")
def analyze_download(count: int = Form(10), handle: str = Form("")) -> dict:
    safe_count = max(1, min(int(count), 50))
    download_file = _find_latest_download_dataset()
    if not download_file:
        raise HTTPException(
            status_code=404,
            detail="No matching Twitter analysis file found in Downloads. Upload file from Excel/CSV File mode.",
        )

    try:
        frame = _read_table_by_suffix(download_file)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to parse download file: {exc}")

    records = frame.fillna("").to_dict(orient="records")
    if handle.strip():
        wanted = handle.strip().lstrip("@").lower()
        filtered: list[dict] = []
        for row in records:
            value = str(row.get("user") or row.get("author.userName") or row.get("username") or "").strip().lstrip("@").lower()
            if value == wanted:
                filtered.append(row)
        records = filtered

    analyzed = engine.analyze_rows(records, safe_count)
    summary = engine.aggregate(analyzed)
    trends = engine.build_trends(analyzed)
    return {
        "summary": summary,
        "rows": analyzed,
        "trends": trends,
        "source": {"type": "downloads", "file": str(download_file)},
    }


# --- FastAPI server startup code ---
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
