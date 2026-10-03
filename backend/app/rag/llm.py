import logging
from abc import ABC, abstractmethod
from functools import lru_cache

import httpx

from app.core.config import get_settings

log = logging.getLogger(__name__)

NO_INFO = "Bu konuda salonun kayıtlarında bilgi bulamadım. Lütfen salon çalışanlarına sorun."

SYSTEM_PROMPT = (
    "Sen bir güzellik salonunun asistanısın. Yalnızca verilen BAĞLAM'daki bilgilere dayanarak, "
    "kısa ve net Türkçe cevap ver. Bağlamda olmayan fiyat, süre veya kişi bilgisi uydurma; "
    "bilmiyorsan 'Bu konuda bilgim yok, lütfen salon çalışanlarına sorun.' de."
)


class LLM(ABC):
    @abstractmethod
    def answer(self, question: str, contexts: list[str], history: list[tuple[str, str]]) -> str: ...


class ExtractiveLLM(LLM):
    """No generative model: returns the retrieved salon facts. Zero hallucination, zero setup."""

    def answer(self, question: str, contexts: list[str], history: list[tuple[str, str]]) -> str:
        if not contexts:
            return NO_INFO
        return "Salon bilgilerine göre:\n" + "\n".join(f"• {c}" for c in contexts[:3])


class OpenAICompatLLM(LLM):
    """Any OpenAI-compatible /chat/completions endpoint (Ollama, vLLM, OpenAI, ...)."""

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url, self.api_key, self.model = base_url.rstrip("/"), api_key, model

    def answer(self, question: str, contexts: list[str], history: list[tuple[str, str]]) -> str:
        if not contexts:
            return NO_INFO
        context = "\n".join(f"- {c}" for c in contexts)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages += [{"role": r, "content": c} for r, c in history[-6:]]
        messages.append({"role": "user", "content": f"BAĞLAM:\n{context}\n\nSORU: {question}"})
        try:
            r = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "messages": messages, "temperature": 0.2, "max_tokens": 300},
                timeout=60,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            log.exception("LLM call failed; falling back to extractive answer")
            return ExtractiveLLM().answer(question, contexts, history)


@lru_cache
def get_llm() -> LLM:
    s = get_settings()
    if s.llm_backend == "openai_compat":
        return OpenAICompatLLM(s.llm_base_url, s.llm_api_key, s.llm_model)
    return ExtractiveLLM()
