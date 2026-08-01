"""Kotoshu HTTP API client.

Thin sync client for the kotoshu-server HTTP API.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable

try:
    import requests
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "kotoshu requires 'requests'; install with: pip install kotoshu"
    ) from exc


@dataclass
class Suggestion:
    word: str
    distance: int = 0
    confidence: float = 1.0
    source: str = "unknown"
    metadata: dict = field(default_factory=dict)


@dataclass
class WordError:
    word: str
    position: int | None
    suggestions: list[Suggestion] = field(default_factory=list)

    @property
    def top_suggestions(self) -> list[str]:
        return [s.word for s in self.suggestions[:3]]


@dataclass
class DocumentResult:
    file: str | None
    word_count: int
    errors: list[WordError] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return not self.errors

    @property
    def misspelled_words(self) -> list[str]:
        return [e.word for e in self.errors]


@dataclass
class Detection:
    language: str | None
    confidence: float


class KotoshuError(Exception):
    """Raised when the kotoshu server returns an error."""


class ResourceNotSetupError(KotoshuError):
    """The requested language is not set up on the server."""


class Client:
    """Sync client for the kotoshu-server HTTP API.

    Args:
        base_url: Base URL, e.g. "http://localhost:9292".
        language: Default language code; can be overridden per call.
        timeout: HTTP timeout in seconds.
        session: Optional requests.Session for connection pooling.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:9292",
        *,
        language: str = "en",
        timeout: float = 30.0,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.default_language = language
        self.timeout = timeout
        self.session = session or requests.Session()

    def health(self) -> dict[str, Any]:
        return self._get("/v1/health")

    def languages(self) -> list[str]:
        return self._get("/v1/languages").get("cached", [])

    def check(
        self,
        text: str,
        *,
        language: str | None = None,
        fmt: str = "full",
    ) -> DocumentResult:
        body = {"text": text, "language": language or self.default_language, "format": fmt}
        raw = self._post("/v1/check", body)
        return DocumentResult(
            file=raw.get("file"),
            word_count=raw.get("word_count", 0),
            errors=[
                WordError(
                    word=e["word"],
                    position=e.get("position"),
                    suggestions=[Suggestion(**s) for s in e.get("suggestions", [])],
                )
                for e in raw.get("errors", [])
            ],
        )

    def suggest(
        self,
        word: str,
        *,
        language: str | None = None,
        max_suggestions: int | None = None,
    ) -> list[Suggestion]:
        body: dict[str, Any] = {"word": word, "language": language or self.default_language}
        if max_suggestions is not None:
            body["max"] = max_suggestions
        raw = self._post("/v1/suggest", body)
        return [Suggestion(**s) for s in raw.get("suggestions", [])]

    def detect(self, text: str) -> Detection:
        raw = self._post("/v1/detect", {"text": text})
        return Detection(language=raw.get("language"), confidence=raw.get("confidence", 0.0))

    def correct(self, word: str, *, language: str | None = None) -> bool:
        """Return True if `word` is in the dictionary (no errors)."""
        result = self.check(word, language=language)
        return result.success

    # ---- Internals ----

    def _get(self, path: str) -> Any:
        url = self.base_url + path
        resp = self.session.get(url, timeout=self.timeout)
        return self._handle(resp)

    def _post(self, path: str, body: dict[str, Any]) -> Any:
        url = self.base_url + path
        resp = self.session.post(url, json=body, timeout=self.timeout)
        return self._handle(resp)

    @staticmethod
    def _handle(resp: requests.Response) -> Any:
        try:
            data = resp.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise KotoshuError(
                f"non-JSON response from server (status={resp.status_code}): {resp.text[:200]}"
            ) from exc
        if 200 <= resp.status_code < 300:
            return data
        err = data.get("error", "http_error")
        msg = data.get("message", resp.text)
        if err == "resource_not_setup":
            raise ResourceNotSetupError(msg)
        raise KotoshuError(f"{err}: {msg}")


__all__ = [
    "Client",
    "DocumentResult",
    "WordError",
    "Suggestion",
    "Detection",
    "KotoshuError",
    "ResourceNotSetupError",
]
