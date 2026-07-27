import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def get_llm():
    return ChatOpenAI(
        model="gpt-oss:20b-cloud",
        api_key=os.environ["OLLAMA_API_KEY"],
        base_url="https://ollama.com/v1",
        temperature=0,
    )