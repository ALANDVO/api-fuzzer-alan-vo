"""Multi-provider LLM adapter supporting OpenAI, Anthropic, Gemini, and Ollama via httpx."""
import json
import re
from typing import Any, Dict, List, Optional
import httpx
from backend.app.core.config import get_settings


class LLMError(Exception):
    """Raised when an LLM provider request fails or returns an unparseable response."""
    pass


def redact_secrets(text: str) -> str:
    """Sanitize error messages and logs to ensure no credentials or sensitive tokens leak."""
    if not text:
        return ""
    # Redact Authorization header values, api keys, and bearer tokens
    text = re.sub(r'(?:bearer\s+|key=)[A-Za-z0-9_-]{12,}', '[REDACTED_CREDENTIAL]', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|sk-or-v1-[a-f0-9]{32,})\b', '[REDACTED_TOKEN]', text)
    settings = get_settings()
    if settings.llm_api_key and settings.llm_api_key in text:
        text = text.replace(settings.llm_api_key, "[REDACTED_API_KEY]")
    return text


class LLMService:
    """Server-side multi-provider LLM adapter with bounded timeouts and error redaction."""

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        settings = get_settings()
        self.provider = (provider or settings.llm_provider).lower()
        self.api_key = api_key if api_key is not None else settings.llm_api_key
        self.model = model or settings.llm_model
        self.base_url = base_url or settings.llm_base_url
        self.timeout = timeout or settings.llm_timeout_seconds

    @property
    def is_configured(self) -> bool:
        """Returns True if the LLM key is present or local Ollama provider is selected."""
        if self.provider == "ollama":
            return True
        return bool(self.api_key and self.api_key.strip())

    async def generate_advisory(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Request advisory reasoning from the configured provider."""
        if not self.is_configured:
            return {
                "success": False,
                "advisory": "LLM provider is not configured. Running in deterministic offline baseline mode.",
                "provider": self.provider,
                "model": self.model,
                "is_advisory": True
            }

        sys_msg = system_prompt or "You are an AI security advisor analyzing API fuzz findings."
        try:
            if self.provider == "anthropic":
                content = await self._call_anthropic(prompt, sys_msg)
            elif self.provider == "gemini":
                content = await self._call_gemini(prompt, sys_msg)
            else:
                # Default: OpenAI-compatible (includes LiteLLM, Ollama, OpenRouter)
                content = await self._call_openai_compatible(prompt, sys_msg)

            return {
                "success": True,
                "advisory": content,
                "provider": self.provider,
                "model": self.model,
                "is_advisory": True
            }
        except Exception as e:
            sanitized_err = redact_secrets(str(e))
            return {
                "success": False,
                "advisory": f"Advisory LLM evaluation failed: {sanitized_err}",
                "provider": self.provider,
                "model": self.model,
                "is_advisory": True,
                "error": sanitized_err
            }

    async def _call_openai_compatible(self, prompt: str, system_prompt: str) -> str:
        base = (self.base_url or "https://api.openai.com/v1").rstrip("/")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 1024
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{base}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _call_anthropic(self, prompt: str, system_prompt: str) -> str:
        base = (self.base_url or "https://api.anthropic.com").rstrip("/")
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key or "",
            "anthropic-version": "2023-06-01"
        }
        payload = {
            "model": self.model,
            "system": system_prompt,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1024,
            "temperature": 0.2
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{base}/v1/messages", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]

    async def _call_gemini(self, prompt: str, system_prompt: str) -> str:
        base = (self.base_url or "https://generativelanguage.googleapis.com").rstrip("/")
        url = f"{base}/v1beta/models/{self.model}:generateContent"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["x-goog-api-key"] = self.api_key

        payload = {
            "contents": [{
                "parts": [{"text": f"{system_prompt}\n\n{prompt}"}]
            }]
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise LLMError("Gemini response contained no candidate parts.")
            return candidates[0]["content"]["parts"][0]["text"]
