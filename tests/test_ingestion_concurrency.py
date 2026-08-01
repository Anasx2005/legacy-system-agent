import pytest

from backend.services.ingestion import PipelineError, _analyst_concurrency


def test_analysts_run_sequentially_by_default(monkeypatch):
    monkeypatch.delenv("INGESTION_ANALYST_CONCURRENCY", raising=False)

    assert _analyst_concurrency() == 1


def test_analyst_concurrency_rejects_out_of_range_values(monkeypatch):
    monkeypatch.setenv("INGESTION_ANALYST_CONCURRENCY", "5")

    with pytest.raises(PipelineError, match="must be between 1 and 4"):
        _analyst_concurrency()
