import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def signature(payload_bytes: bytes, secret: str) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()

    return f"sha256={digest}"


def test_rejects_webhook_when_secret_is_missing(monkeypatch):
    monkeypatch.delenv("GITHUB_WEBHOOK_SECRET", raising=False)

    response = client.post(
        "/webhooks/github",
        content=b"{}",
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "sha256=invalid",
        },
    )

    assert response.status_code == 401


def test_rejects_webhook_with_invalid_signature(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-secret")

    payload = json.dumps({}).encode("utf-8")

    response = client.post(
        "/webhooks/github",
        content=payload,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "sha256=wrong-signature",
        },
    )

    assert response.status_code == 401


def test_ignores_valid_non_pull_request_event(monkeypatch):
    secret = "test-secret"
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", secret)
    monkeypatch.setenv(
        "GITHUB_MODEL_REPO",
        "Anasx2005/legacy-system-model",
    )

    payload = {
        "repository": {
            "full_name": "Anasx2005/legacy-system-model",
        },
    }

    raw_payload = json.dumps(payload).encode("utf-8")

    response = client.post(
        "/webhooks/github",
        content=raw_payload,
        headers={
            "X-GitHub-Event": "ping",
            "X-Hub-Signature-256": signature(raw_payload, secret),
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ignored"