import logging
import asyncio
import json
from typing import List, Dict, Any, Optional
from groq import AsyncGroq
from core.config import settings

logger = logging.getLogger(__name__)

class GroqClient:
    # ── Verified-active models (April 2026) ──────────────────────────────────
    # Production (stable, never deprecated without 30-day notice):
    #   llama-3.1-8b-instant, llama-3.3-70b-versatile
    # Preview (active, may change with short notice):
    #   meta-llama/llama-4-scout-17b-16e-instruct, qwen/qwen3-32b
    MODELS = [
        "llama-3.1-8b-instant",                       # production — fast, preferred
        "llama-3.3-70b-versatile",                     # production — most capable
        "meta-llama/llama-4-scout-17b-16e-instruct",  # preview fallback
        "qwen/qwen3-32b",                              # preview final fallback
    ]

    # Allow 3 parallel LLM calls — enough for light concurrency without blasting limits
    _semaphore = asyncio.Semaphore(3)

    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY, timeout=30.0, max_retries=0)

    async def generate_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.1, preferred_model: str = None) -> Dict:
        """Runs completion with exponential backoff on 429s and automatic model fallback."""
        last_error = None

        models_to_try = [preferred_model] + [m for m in self.MODELS if m != preferred_model] if preferred_model else self.MODELS
        production_models = {"llama-3.1-8b-instant", "llama-3.3-70b-versatile"}

        for model in models_to_try:
            # If we've exhausted production models and are about to try a preview model,
            # wait briefly to let the rate-limit window reset a little
            if model not in production_models:
                await asyncio.sleep(0.5)

            # Give every model a few retries to handle transient rate limits
            max_retries = 3 if model in production_models else 2
            
            for attempt in range(max_retries):
                try:
                    async with self._semaphore:
                        response = await self.client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            temperature=temperature,
                            response_format={"type": "json_object"},
                            max_tokens=2048
                        )

                    content = response.choices[0].message.content.strip()
                    if content.startswith("```"):
                        content = content.split("```")[1].replace("json", "").strip()
                    return json.loads(content)

                except Exception as e:
                    err_msg = str(e).lower()
                    if "rate_limit_exceeded" in err_msg or "429" in err_msg:
                        last_error = e
                        if attempt < max_retries - 1:
                            backoff = min(2 ** attempt + 1, 5)  # 2s, 3s, max 5s
                            logger.warning(f"Groq Rate Limit (429) on {model}. Retrying in {backoff}s (attempt {attempt+1}/{max_retries})...")
                            await asyncio.sleep(backoff)
                            continue
                        else:
                            logger.warning(f"Groq Rate Limit (429) on {model}. Exhausted retries. Falling back to next model...")
                            break
                    elif "400" in err_msg or "decommissioned" in err_msg or "model_decommissioned" in err_msg:
                        logger.warning(f"Groq Model {model} decommissioned/rejected. Falling back to next model...")
                        last_error = e
                        break
                    elif "500" in err_msg or "503" in err_msg:
                        logger.warning(f"Groq Server Error on {model}. Falling back to next model...")
                        last_error = e
                        break
                    else:
                        logger.error(f"Unexpected Groq error on {model}: {e}")
                        raise e

        raise last_error or Exception("All Groq models failed.")

    async def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.2, preferred_model: str = None) -> str:
        """Runs completion with exponential backoff on 429s and automatic model fallback."""
        last_error = None

        models_to_try = [preferred_model] + [m for m in self.MODELS if m != preferred_model] if preferred_model else self.MODELS
        production_models = {"llama-3.1-8b-instant", "llama-3.3-70b-versatile"}

        for model in models_to_try:
            if model not in production_models:
                await asyncio.sleep(0.5)

            # Give every model a few retries to handle transient rate limits
            max_retries = 3 if model in production_models else 2
            
            for attempt in range(max_retries):
                try:
                    async with self._semaphore:
                        response = await self.client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            temperature=temperature,
                            max_tokens=4096
                        )
                    return response.choices[0].message.content.strip()

                except Exception as e:
                    err_msg = str(e).lower()
                    if "rate_limit_exceeded" in err_msg or "429" in err_msg:
                        last_error = e
                        if attempt < max_retries - 1:
                            backoff = min(2 ** attempt + 1, 5)  # 2s, 3s, max 5s
                            logger.warning(f"Groq Rate Limit (429) on {model}. Retrying in {backoff}s (attempt {attempt+1}/{max_retries})...")
                            await asyncio.sleep(backoff)
                            continue
                        else:
                            logger.warning(f"Groq Rate Limit (429) on {model}. Exhausted retries. Falling back to next model...")
                            break
                    elif "400" in err_msg or "decommissioned" in err_msg or "model_decommissioned" in err_msg:
                        logger.warning(f"Groq Model {model} decommissioned/rejected. Falling back to next model...")
                        last_error = e
                        break
                    elif "500" in err_msg or "503" in err_msg:
                        logger.warning(f"Groq Server Error on {model}. Falling back to next model...")
                        last_error = e
                        break
                    else:
                        logger.error(f"Unexpected Groq error on {model}: {e}")
                        raise e

        raise last_error or Exception("All Groq models failed.")

# Global instance
groq_client = GroqClient()
