from backend.services import ingestion


def test_subagent_retries_with_gemini_when_primary_provider_returns_500(monkeypatch):
    calls = []
    fallback_model = object()

    class PrimaryAgent:
        def invoke(self, *_args, **_kwargs):
            raise RuntimeError("openai.InternalServerError: Error code: 500")

    class FallbackAgent:
        def invoke(self, *_args, **_kwargs):
            calls.append("fallback-invoked")

    def fake_create_base_agent(*, model=None):
        calls.append(model)
        return FallbackAgent() if model is fallback_model else PrimaryAgent()

    monkeypatch.setattr(ingestion, "create_base_agent", fake_create_base_agent)
    monkeypatch.setattr(ingestion, "get_fallback_llm", lambda: fallback_model)

    ingestion._invoke_subagent("strategy-analyst", "run-fallback")

    assert calls == [None, fallback_model, "fallback-invoked"]
