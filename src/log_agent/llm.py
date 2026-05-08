"""로컬 LLM 서버(Ollama/vLLM) 호출을 추상화한다."""


def complete(prompt: str, *, system: str | None = None) -> str:
    """프롬프트를 LLM 에 보내고 원시 응답 문자열을 반환한다."""
    raise NotImplementedError
