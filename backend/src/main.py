


import os
from contextlib import asynccontextmanager
from typing import Optional

# Import centralized config
from config import settings
# Unified logging setup
from config.logging_config import logger

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx
import yfinance as yf

# Import AI controller
from controllers.ai_controller import handle_ai_ask
# Import Pydantic models
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


## All config and constants are now loaded from config/settings.py

try:
    import google.generativeai as genai
except Exception:
    genai = None


# ---------- Lifespan ----------
# ---------- AI Route ----------

@app.post("/ai/ask", response_model=AskResponse)
async def ai_ask(req: AskRequest, request: Request):
    """AI Assistant endpoint."""
    text = await handle_ai_ask(req.query, req.portfolio)
    return {"response_text": text}

    try:
        loop = asyncio.get_running_loop()
        
        safety_settings = {
            'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
            'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
            'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
            'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
        }

        response = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.2,
                        "max_output_tokens": settings.MAX_OUTPUT_TOKENS,
                    },
                    safety_settings=safety_settings,
                ),
            ),
            timeout=settings.AI_TIMEOUT_SECONDS,
        )

        print("\n===== RAW GEMINI RESPONSE START =====")
        print(response)
        print("===== RAW GEMINI RESPONSE END =====\n")

        if not response.candidates:
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                block_reason = response.prompt_feedback.block_reason
                logger.warning(f"Prompt blocked due to: {block_reason}")
                return {"response_text": f"⚠️ Your query was blocked by the safety filter: {block_reason}. Please rephrase your question."}
            else:
                logger.warning("No candidates returned from Gemini.")
                return {"response_text": "⚠️ The AI model did not return a response. This might be due to a content filter or an internal error. Please try again."}

        text = ""
        try:
            if response.candidates:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    text = "".join(part.text for part in candidate.content.parts if part.text)

            if not text:
                logger.warning("No text found in Gemini response. Finish reason: %s", candidate.finish_reason if 'candidate' in locals() else 'N/A')
                text = "⚠️ The AI model returned an empty response. Please try again."

        except (IndexError, AttributeError) as e:
            logger.error(f"Error extracting text from response: {e}")
            text = "⚠️ Could not read the Gemini response. The format was unexpected."

    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="AI service timeout")
    except Exception as e:
        logger.exception("Error calling Gemini: %s", e)
        raise HTTPException(status_code=502, detail="AI service error")

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
