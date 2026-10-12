from langchain_ollama import ChatOllama

from src.config import MODEL, OLLAMA_BASE_URL, TEMPERATURE


def get_llm() -> ChatOllama:
    return ChatOllama(
        model=MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=TEMPERATURE,
    )