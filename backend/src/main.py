import os
import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import yfinance as yf

# ===============================
# 🔑 Config and Constants
# ===============================
GEMINI_API_KEY = "AIzaSyAdXQlqtuDic-DeRmY0hGFd-472gJ2FjaA"
FRONTEND_ORIGINS = "http://localhost:3000"
FINANCEHUB_API_KEY = "d2ccu61r01qihtcr6m2gd2ccu61r01qihtcr6m30"

MAX_PROMPT_CHARS = 2000
AI_TIMEOUT_SECONDS = 20
MAX_OUTPUT_TOKENS = 512
# ===============================

try:
    import google.generativeai as genai
except Exception:
    genai = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vittcott-backend")

# ---------- Lifespan ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Gemini model on startup."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")

    if genai is None:
        raise RuntimeError("google-generativeai not installed. Run: pip install google-generativeai")

    genai.configure(api_key=GEMINI_API_KEY)

    try:
        try_model = "models/gemini-2.5-pro"
        fallback_model = "models/gemini-pro-latest"
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
    allow_origins=[FRONTEND_ORIGINS, "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Models ----------
class AskRequest(BaseModel):
    query: str
    portfolio: Optional[dict] = None

class AskResponse(BaseModel):
    response_text: str

# ---------- Root ----------
@app.get("/")
async def root():
    return {"message": "Vittcott Backend Running ✅"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/ready")
async def ready():
    return {"ready": hasattr(app.state, "model") and app.state.model is not None}

# ---------- AI Route ----------

@app.post("/ai/ask", response_model=AskResponse)
async def ai_ask(req: AskRequest, request: Request):
    """AI Assistant endpoint."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query must be non-empty")

    query = req.query.strip()
    if len(query) > MAX_PROMPT_CHARS:
        query = query[:MAX_PROMPT_CHARS] + " ... (truncated)"
        logger.warning("Truncated query to %d chars", MAX_PROMPT_CHARS)

    prompt = f"""
You are VITTCOTT AI Advisor — a friendly, beginner-focused investing assistant.
User question: {query}
Portfolio (JSON): {req.portfolio}
Constraints:
- Keep explanation simple and beginner-friendly.
- Include short definitions for any finance terms used.
- Provide up to 3 actionable next steps.
- If more info is needed, ask 1-2 clarifying questions.
"""

    model = getattr(app.state, "model", None)
    if model is None:
        raise HTTPException(status_code=500, detail="AI model not initialized")

    try:
        loop = asyncio.get_running_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.2,
                        "max_output_tokens": MAX_OUTPUT_TOKENS,
                    },
                ),
            ),
            timeout=AI_TIMEOUT_SECONDS,
        )

        # ✅ PRINT RAW GEMINI RESPONSE
        print("\n===== RAW GEMINI RESPONSE START =====")
        print(response)
        print("===== RAW GEMINI RESPONSE END =====\n")

    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="AI service timeout")
    except Exception as e:
        logger.exception("Error calling Gemini: %s", e)
        raise HTTPException(status_code=502, detail="AI service error")

    # ✅ Robust Parsing for Gemini API
    text = None
    try:
        # 1️⃣ If `.text` exists and is valid
        if hasattr(response, "text") and isinstance(response.text, str):
            text = response.text.strip()

        # 2️⃣ Check for structured response in candidates
        elif hasattr(response, "candidates") and response.candidates:
            for cand in response.candidates:
                content = getattr(cand, "content", None)
                if content and hasattr(content, "parts"):
                    for part in content.parts:
                        if hasattr(part, "text") and part.text:
                            text = part.text.strip()
                            break
                if text:
                    break

        # 3️⃣ Attempt deeper access
        if not text and hasattr(response, "candidates"):
            try:
                text = response.candidates[0].content.parts[0].text.strip()
            except Exception:
                pass

        # 4️⃣ Final fallback
        if not text or not isinstance(text, str):
            text = str(response)

    except Exception as e:
        logger.warning(f"⚠️ Gemini parsing error: {e}")
        text = f"⚠️ Could not read Gemini response ({e})"

    # ✅ Ensure text is always valid
    if not text or text.strip() == "":
        text = "⚠️ Gemini returned no response. Try again later." \
        "This can happen if your question was filtered or ambiguous.\n"
        "Try rephrasing your query or asking something simpler (e.g. about stocks, ETFs, or finance basics)."

    return {"response_text": text}

    # ---------- Robust Response Extraction ----------
    text = None
    try:
        # ✅ Handle both .text and candidate formats
        if hasattr(response, "text") and isinstance(response.text, str):
            text = response.text.strip()
        elif hasattr(response, "candidates") and response.candidates:
            for cand in response.candidates:
                if hasattr(cand, "content") and hasattr(cand.content, "parts"):
                    for part in cand.content.parts:
                        if hasattr(part, "text"):
                            text = part.text.strip()
                            break
                if text:
                    break

        if not text:
            text = str(response)
    except Exception as e:
        text = f"⚠️ Could not parse Gemini response ({e})"

    if not text or text.strip() == "":
        text = "⚠️ No meaningful response received from Gemini."

    return {"response_text": text}

# ---------- FinanceHub Proxy ----------
@app.get("/api/finance/quote")
async def finance_quote(symbol: str, range: str = "1d"):
    """Stock data via FinanceHub or fallback yfinance."""
    if FINANCEHUB_API_KEY:
        url = f"https://api.financehub.example/v1/market/quotes?symbol={symbol}&range={range}"
        headers = {"Authorization": f"Bearer {FINANCEHUB_API_KEY}"}
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

# ---------- Run ----------
def _start_uvicorn():
    try:
        import uvicorn
    except Exception:
        logger.error("uvicorn not installed. Run: pip install uvicorn")
        raise

    reload_flag = os.getenv("RELOAD", "false").lower() in ("1", "true", "yes")
    os.chdir(os.path.dirname(__file__))
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=reload_flag)

if __name__ == "__main__":
    _start_uvicorn()
