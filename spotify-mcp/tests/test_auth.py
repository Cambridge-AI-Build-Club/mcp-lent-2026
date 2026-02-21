import json
from pathlib import Path
from unittest.mock import patch

from spotify_mcp.auth import _load_tokens, _save_tokens


def test_save_and_load_tokens(tmp_path):
    token_file = tmp_path / "tokens.json"
    tokens = {"access_token": "abc", "refresh_token": "xyz"}

    with patch("spotify_mcp.auth.TOKEN_PATH", token_file):
        _save_tokens(tokens)
        loaded = _load_tokens()

    assert loaded == tokens


def test_load_tokens_missing(tmp_path):
    token_file = tmp_path / "nonexistent.json"
    with patch("spotify_mcp.auth.TOKEN_PATH", token_file):
        assert _load_tokens() is None


def test_get_credentials_missing(monkeypatch):
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)

    from spotify_mcp.auth import _get_credentials
    import pytest

    with pytest.raises(RuntimeError, match="SPOTIFY_CLIENT_ID"):
        _get_credentials()


def test_get_credentials_present(monkeypatch):
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "test-id")
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "test-secret")

    from spotify_mcp.auth import _get_credentials

    cid, csecret = _get_credentials()
    assert cid == "test-id"
    assert csecret == "test-secret"
