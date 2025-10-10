import os
import time
import uuid
import asyncio
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import httpx
import yfinance as yf
import boto3
from pydantic import BaseModel

# Internal imports
from config import settings
from config.logging_config import logger
from controllers.ai_controller import handle_ai_ask
from models.ai_models import AskRequest, AskResponse

# ---------- Lifespan ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Gemini model on startup."""
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")

    try:
        import google.generativeai as genai
    except Exception:
        genai = None

    if genai is None:
        raise RuntimeError("google-generativeai not installed. Run: pip install google-generativeai")

    genai.configure(api_key=settings.GEMINI_API_KEY)

    try:
        try_model = "models/gemini-2.5-flash"
        fallback_model = "models/gemini-2.5-pro-latest"
        try:
            app.state.model = genai.GenerativeModel(try_model)
            logger.info(f"✅ Initialized Gemini model: {try_model}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to init {try_model} ({e}), falling back to {fallback_model}")
            app.state.model = genai.GenerativeModel(fallback_model)
            logger.info(f"✅ Initialized Gemini model: {fallback_model}")
        yield
    finally:
        if hasattr(app.state, "model"):
            del app.state.model
            logger.info("🧹 Cleaned up Gemini model")


# ---------- App ----------
app = FastAPI(title="VITTCOTT Unified Backend", version="1.0", lifespan=lifespan)

# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # for local frontend dev
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Root Route ----------
@app.get("/api")
def read_root():
    return {"message": "Welcome to VittCott Backend!"}


# ---------- AI Route ----------
@app.post("/api/ai/ask", response_model=AskResponse)
async def ai_ask(req: AskRequest, request: Request):
    """AI Assistant endpoint."""
    text = await handle_ai_ask(req.query, req.portfolio)
    return {"response_text": text}


# ---------- FinanceHub Proxy ----------
@app.get("/api/finance/quote")
async def finance_quote(symbol: str, range: str = "1d"):
    """Stock data via FinanceHub or fallback yfinance."""
    if settings.FINANCEHUB_API_KEY:
        url = f"https://api.financehub.example/v1/market/quotes?symbol={symbol}&range={range}"
        headers = {"Authorization": f"Bearer {settings.FINANCEHUB_API_KEY}"}
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(url, headers=headers, timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    return {
                        "symbol": symbol,
                        "range": range,
                        "price": data.get("price"),
                        "change": data.get("change"),
                        "candles": data.get("candles") or [],
                        "raw": data,
                    }
        except Exception as e:
            logger.warning("FinanceHub failed, falling back to yfinance: %s", e)

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1mo", interval="1d")
        candles = [
            {
                "ts": idx.isoformat(),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]),
            }
            for idx, row in hist.iterrows()
        ]
        price = candles[-1]["close"] if candles else None
        return {"symbol": symbol, "range": range, "price": price, "candles": candles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stock data error: {e}")


# ---------- Presign / Upload helpers (copied from presign_app.py) ----------
# ---------- Presign / Upload helpers ----------
import boto3
from botocore.config import Config as BotocoreConfig

# ✅ Force AWS region to ap-south-1 everywhere
AWS_REGION = "ap-south-1"
BUCKET = os.getenv("S3_BUCKET", "vittcott-uploads-xyz123")
DDB_TABLE = os.getenv("DDB_TABLE", "user_files")

# Override every possible region source
os.environ["AWS_REGION"] = AWS_REGION
os.environ["AWS_DEFAULT_REGION"] = AWS_REGION
boto3.setup_default_session(region_name=AWS_REGION)

# ✅ Create a *fresh* session (not cached)
session = boto3.session.Session(region_name=AWS_REGION)

# ✅ Explicit config to ensure signature v4
boto_config = BotocoreConfig(
    region_name=AWS_REGION,
    signature_version="s3v4"
)

# ✅ Instantiate new S3 client (freshly bound to ap-south-1)
s3 = session.client("s3", config=boto_config)

print(f"[DEBUG] Using region: {AWS_REGION}")
print(f"[DEBUG] boto3 session region: {session.region_name}")

class PresignReq(BaseModel):
    filename: str
    content_type: str
    username: str

@app.post("/presign")
def presign(req: PresignReq):
    key = f"users/{req.username}/{int(time.time())}_{uuid.uuid4().hex}_{req.filename}"
    conditions = [
        ["content-length-range", 0, 10 * 1024 * 1024],
        {"Content-Type": req.content_type}
    ]
    fields = {"Content-Type": req.content_type}

    try:
        presigned = s3.generate_presigned_post(
            Bucket=BUCKET,
            Key=key,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=3600
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "url": presigned["url"],
        "fields": presigned["fields"],
        "key": key
    }


@app.post("/register")
def register(payload: dict):
    try:
        username = payload["username"]
        s3_key = payload["s3_key"]
        filename = payload.get("filename", "")
        size = int(payload.get("size", 0))
    except Exception:
        raise HTTPException(status_code=400, detail="missing fields")

    item = {
        "username": username,
        "uploaded_at": int(time.time()),
        "s3_key": s3_key,
        "filename": filename,
        "size": size,
    }

    # write to DynamoDB if table available (safe to skip in dev)
    try:
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(DDB_TABLE)
        table.put_item(Item=item)
    except Exception as e:
        logger.warning("DynamoDB write error (ignored in dev): %s", e)

    # presigned GET for convenience
    try:
        download_url = s3.generate_presigned_url(
            "get_object", Params={"Bucket": BUCKET, "Key": s3_key}, ExpiresIn=3600
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"couldn't make download url: {e}")

    return {"ok": True, "download_url": download_url, "s3_key": s3_key}

# ---------- Static Frontend Mount ----------
# Copy your frontend files into backend/src/frontend_build (public + src/pages)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "frontend_build")

if not os.path.isdir(STATIC_DIR):
    print(f"[⚠️] Static directory not found: {STATIC_DIR}. Run your copy script or move frontend/public here.")

# Serve explicit asset and pages folders first to avoid ambiguous routing and ensure
# CSS/JS/images are always served at /assets/* and pages at /pages/*.
assets_dir = os.path.join(STATIC_DIR, "assets")
pages_dir = os.path.join(STATIC_DIR, "pages")

if os.path.isdir(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
else:
    logger.warning("Static assets directory not found: %s", assets_dir)

if os.path.isdir(pages_dir):
    app.mount("/pages", StaticFiles(directory=pages_dir), name="pages")
else:
    logger.warning("Static pages directory not found: %s", pages_dir)

# Fallback: mount the full frontend (serves index.html for SPA routes)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")

# Optional SPA fallback (for routing in frontend)
@app.exception_handler(404)
async def spa_fallback(request: Request, exc):
    accept = request.headers.get("accept", "")
    index_path = os.path.join(STATIC_DIR, "index.html")
    if "text/html" in accept and os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(status_code=404, content={"detail": "Not Found"})


# ---------- Run ----------
def _start_uvicorn():
    try:
        import uvicorn
    except Exception:
        logger.error("uvicorn not installed. Run: pip install uvicorn")
        raise

    os.chdir(os.path.dirname(__file__))
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT, reload=settings.RELOAD)


if __name__ == "__main__":
    _start_uvicorn()
