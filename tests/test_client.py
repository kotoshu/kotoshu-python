"""Smoke test against a live kotoshu-server.

Run with: python -m pytest tests/test_client.py
Set KOTOSHU_TEST_URL to point at a different server.
"""

import os

import pytest

from kotoshu import Client, DocumentResult, KotoshuError


@pytest.fixture(scope="module")
def client():
    url = os.environ.get("KOTOSHU_TEST_URL", "http://localhost:9292")
    c = Client(url)
    try:
        c.health()
    except Exception as exc:
        pytest.skip(f"no kotoshu server at {url}: {exc}")
    return c


def test_check_flags_misspelled(client):
    result = client.check("helo wrold", language="en")
    assert isinstance(result, DocumentResult)
    assert "helo" in result.misspelled_words
    assert "wrold" in result.misspelled_words


def test_check_passes_correct_text(client):
    result = client.check("hello world", language="en")
    assert result.success
    assert result.misspelled_words == []


def test_suggest_returns_suggestions(client):
    suggestions = client.suggest("helo", language="en", max_suggestions=3)
    assert len(suggestions) <= 3
    assert any(s.word == "hello" for s in suggestions)


def test_detect_returns_language(client):
    detection = client.detect("hello world")
    assert detection.language is not None
    assert 0.0 <= detection.confidence <= 1.0


def test_correct_helper(client):
    assert client.correct("hello", language="en") is True
    assert client.correct("helo", language="en") is False


def test_languages_endpoint(client):
    langs = client.languages()
    assert isinstance(langs, list)
    assert "en" in langs


def test_error_on_missing_text(client):
    with pytest.raises(KotoshuError):
        # Bypass client-side validation to hit the 400 path
        client._post("/v1/check", {"language": "en"})
