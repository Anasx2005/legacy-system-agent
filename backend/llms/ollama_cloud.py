import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

# Keep a transient-provider retry bounded. Ingestion runs five agents, so a
# long timeout here multiplies into an unusable overall job duration.
DEFAULT_TIMEOUT_SECONDS = 45
DEFAULT_MAX_RETRIES = 2


def get_llm():
    """Create the hosted Ollama model with resilience for transient 5xx errors."""
    return ChatOpenAI(
        model="gpt-oss:20b-cloud",
        api_key=os.environ["OLLAMA_API_KEY"],
        base_url="https://ollama.com/v1",
        temperature=0,
        timeout=int(os.getenv("OLLAMA_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)),
        max_retries=int(os.getenv("OLLAMA_MAX_RETRIES", DEFAULT_MAX_RETRIES)),
    )
