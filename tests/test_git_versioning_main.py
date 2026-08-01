from types import SimpleNamespace

import pytest

from agents import git_versioning


def test_switch_to_main_preserves_generated_output(monkeypatch, tmp_path):
    calls = []

    def fake_git(args, *, cwd, **kwargs):
        calls.append((args, kwargs))
        if args == ["branch", "--show-current"]:
            return SimpleNamespace(stdout="feature/ingest-legacy-system-run-002\n", returncode=0)
        if args == ["switch", "main", "--merge"]:
            return SimpleNamespace(stdout="", stderr="", returncode=0)
        raise AssertionError(f"Unexpected Git call: {args}")

    monkeypatch.setattr(git_versioning, "git", fake_git)

    git_versioning.switch_to_main_preserving_model_output(tmp_path)

    assert calls[1] == (["switch", "main", "--merge"], {"check": False})


def test_switch_to_main_reports_conflict_without_resetting_files(monkeypatch, tmp_path):
    def fake_git(args, *, cwd, **kwargs):
        if args == ["branch", "--show-current"]:
            return SimpleNamespace(stdout="feature/old-run\n", returncode=0)
        return SimpleNamespace(stdout="", stderr="local changes would be overwritten", returncode=1)

    monkeypatch.setattr(git_versioning, "git", fake_git)

    with pytest.raises(RuntimeError, match="could not safely return"):
        git_versioning.switch_to_main_preserving_model_output(tmp_path)
