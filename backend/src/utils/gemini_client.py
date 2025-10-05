import logging
import asyncio
from config import settings

try:
    import google.generativeai as genai
except Exception:
    genai = None

logger = logging.getLogger("vittcott-backend")

class GeminiClient:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY not set")
        if genai is None:
            raise RuntimeError("google-generativeai not installed. Run: pip install google-generativeai")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.try_model = "models/gemini-2.5-flash"
        self.fallback_model = "models/gemini-2.5-pro-latest"
        self.model = None
        self._init_model()

    def _init_model(self):
        try:
            self.model = genai.GenerativeModel(self.try_model)
            logger.info(f"✅ Initialized Gemini model: {self.try_model}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to init {self.try_model} ({e}), falling back to {self.fallback_model}")
            self.model = genai.GenerativeModel(self.fallback_model)
            logger.info(f"✅ Initialized Gemini model: {self.fallback_model}")

    async def generate_content(self, prompt: str, temperature: float = 0.2, max_output_tokens: int = None, safety_settings: dict = None, timeout: int = None):
        if not self.model:
            self._init_model()
        loop = asyncio.get_running_loop()
        max_tokens = max_output_tokens or settings.MAX_OUTPUT_TOKENS
        timeout = timeout or settings.AI_TIMEOUT_SECONDS
        safety_settings = safety_settings or {
            'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
            'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
            'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
            'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
        }
        try:
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self.model.generate_content(
                        prompt,
                        generation_config={
                            "temperature": temperature,
                            "max_output_tokens": max_tokens,
                        },
                        safety_settings=safety_settings,
                    ),
                ),
                timeout=timeout,
            )
            return response
        except asyncio.TimeoutError:
            raise
        except Exception as e:
            logger.exception("Error calling Gemini: %s", e)
            raise

    @staticmethod
    def extract_text(response):
        if not response or not getattr(response, 'candidates', None):
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback and response.prompt_feedback.block_reason:
                return f"⚠️ Your query was blocked by the safety filter: {response.prompt_feedback.block_reason}. Please rephrase your question."
            return "⚠️ The AI model did not return a response. This might be due to a content filter or an internal error. Please try again."
        try:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                text = "".join(part.text for part in candidate.content.parts if part.text)
                if text:
                    return text
            finish_reason = getattr(candidate, 'finish_reason', 'N/A')
            return f"⚠️ The AI model returned an empty response. Please try again. (Finish reason: {finish_reason})"
        except (IndexError, AttributeError) as e:
            logger.error(f"Error extracting text from response: {e}")
            return "⚠️ Could not read the Gemini response. The format was unexpected."
