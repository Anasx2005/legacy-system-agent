from backend.llms import ollama_cloud


def test_hosted_ollama_client_retries_transient_failures(monkeypatch):
    captured = {}

    def fake_chat_openai(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setenv("OLLAMA_API_KEY", "test-key")
    monkeypatch.setattr(ollama_cloud, "ChatOpenAI", fake_chat_openai)

    ollama_cloud.get_llm()

    assert captured["model"] == "gpt-oss:20b-cloud"
    assert captured["base_url"] == "https://ollama.com/v1"
    assert captured["timeout"] == 45
    assert captured["max_retries"] == 2
