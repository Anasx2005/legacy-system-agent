import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()


def get_llm():
    return ChatGroq(
        model="qwen/qwen3.6-27b",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0,
    )