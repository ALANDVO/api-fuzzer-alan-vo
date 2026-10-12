"""Legacy compatibility adapter for LLM client."""
import asyncio
from backend.app.services.llm_service import LLMService


class LLM:
    """Compatibility wrapper delegating to backend LLMService."""

    def __init__(self):
        self.service = LLMService()

    def generate(self, prompt: str, system: str = "") -> str:
        res = asyncio.run(self.service.generate_advisory(prompt, system))
        return res.get("advisory", "")
