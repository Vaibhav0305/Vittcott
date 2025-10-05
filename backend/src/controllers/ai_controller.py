
from fastapi import HTTPException
from config import settings
from utils.gemini_client import GeminiClient
from utils.prompts import AI_ASSISTANT_PROMPT
from config.logging_config import logger

gemini_client = GeminiClient()

async def handle_ai_ask(query: str, portfolio: dict = None):
    if not query.strip():
        raise HTTPException(status_code=400, detail="query must be non-empty")
    q = query.strip()
    if len(q) > settings.MAX_PROMPT_CHARS:
        q = q[:settings.MAX_PROMPT_CHARS] + " ... (truncated)"
        logger.warning("Truncated query to %d chars", settings.MAX_PROMPT_CHARS)
    prompt = AI_ASSISTANT_PROMPT.format(query=q, portfolio=portfolio)
    try:
        response = await gemini_client.generate_content(prompt)
        logger.info("Gemini raw response: %s", response)
        text = GeminiClient.extract_text(response)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in Gemini AI controller: %s", e)
        raise HTTPException(status_code=502, detail="AI service error")
    return text
