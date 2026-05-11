"""로컬 LLM 서버(Ollama) 호출을 추상화한다."""

import os

import httpx

_TIMEOUT_SECONDS = 120.0


def complete(prompt: str, *, system: str | None = None) -> str:
    """프롬프트를 Ollama 에 보내고 LLM 응답 문자열을 그대로 반환한다.

    Ollama HTTP envelope 만 파싱하고, 본문(예: JSON) 검증은 호출자(analyzer) 책임.
    """
    base_url = os.environ["LLM_BASE_URL"].rstrip("/")
    model = os.environ["LLM_MODEL"]

    messages: list[dict[str, str]] = []
    if system is not None:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = httpx.post(
        f"{base_url}/api/chat",
        json={"model": model, "messages": messages, "stream": False},
        timeout=_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]
