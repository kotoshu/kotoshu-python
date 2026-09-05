"""Optional native (Rust) engine backend.

Wraps the ``kotoshu_native`` extension module -- the ``kotoshu-native``
wheel built from the kotoshu-rs repository -- behind the same result
shapes the HTTP client returns, so ``Suggestion`` objects are identical
across backends.

The wheel is published on PyPI (``pip install kotoshu-native``, or
``pip install kotoshu[native]``); platform wheels cover linux
x86_64/aarch64, macOS x86_64/arm64 and windows x64 from the first
matrix-built release onward -- until such a release reaches PyPI, some
platforms compile from source (needs a Rust toolchain). Without the
module ``available()`` is False and the default ``auto`` backend quietly
falls back to HTTP (see README, "Native backend").
"""

from __future__ import annotations

import os
from types import ModuleType
from typing import Any

from . import KotoshuError, Suggestion

try:
    import kotoshu_native as _native
except ImportError:  # the wheel is not installed; see module docstring
    _native = None

#: Environment variable selecting the backend: "native", "http" or "auto".
ENV_VAR = "KOTOSHU_BACKEND"

NATIVE = "native"
HTTP = "http"
AUTO = "auto"

_UNAVAILABLE_MESSAGE = (
    "the native backend was requested (KOTOSHU_BACKEND=native) but the "
    "'kotoshu_native' extension module could not be imported.\n"
    "Install the wheel from PyPI: pip install kotoshu-native\n"
    "(or pip install kotoshu[native]); on a platform without a prebuilt "
    "wheel this compiles from source, which needs a Rust toolchain. "
    "Alternatively build it locally from the kotoshu-rs repository:\n"
    "  python3 -m venv .venv && . .venv/bin/activate\n"
    "  pip install maturin\n"
    "  maturin develop   # inside kotoshu-rs/kotoshu-python\n"
    "Or keep using the HTTP backend: KOTOSHU_BACKEND=http"
)


class NativeUnavailableError(KotoshuError):
    """The native backend was requested but kotoshu_native is missing."""


def available() -> bool:
    """Return True when the kotoshu_native extension module is importable."""
    return _native is not None


def resolve_backend(setting: str | None, native_available: bool) -> str:
    """Resolve a KOTOSHU_BACKEND value to "native" or "http".

    Pure decision function (no environment, no imports): `setting` is the
    raw env value (None or empty means "auto"), `native_available` is
    whether kotoshu_native imports. Raises NativeUnavailableError when
    "native" is forced but unavailable, ValueError for anything else.
    """
    choice = (setting or AUTO).strip().lower()
    if choice == AUTO:
        return NATIVE if native_available else HTTP
    if choice == HTTP:
        return HTTP
    if choice == NATIVE:
        if not native_available:
            raise NativeUnavailableError(_UNAVAILABLE_MESSAGE)
        return NATIVE
    raise ValueError(
        f"invalid {ENV_VAR}={setting!r}: expected 'native', 'http' or 'auto'"
    )


def backend() -> str:
    """Return the backend in effect: "native" or "http".

    Honors KOTOSHU_BACKEND (native|http|auto; default auto: native when
    the wheel is importable, else http). Raises NativeUnavailableError
    when "native" is forced but the module is missing.
    """
    return resolve_backend(os.environ.get(ENV_VAR), available())


class Dictionary:
    """A loaded native dictionary -- the offline twin of ``Client``.

    Instances are created by :meth:`load` or
    ``NativeBackend.dictionary``. ``correct``/``suggest`` return exactly
    the shapes the HTTP client returns, so result handling is identical
    across backends. Word-level only: the offline engine has no document
    parsing and no language detection.
    """

    def __init__(self, module: ModuleType, impl: Any) -> None:
        self._module = module
        self._impl = impl

    @classmethod
    def load(cls, aff_path: str, dic_path: str) -> Dictionary:
        """Load Hunspell .aff/.dic files through the native engine."""
        return _load_via(_required_module(), aff_path, dic_path)

    def correct(self, word: str) -> bool:
        """Return True if `word` is in the dictionary (no errors)."""
        try:
            return bool(self._impl.correct(word))
        except self._module.KotoshuNativeError as exc:
            raise KotoshuError(f"native check failed: {exc}") from exc

    def suggest(
        self,
        word: str,
        *,
        max_suggestions: int = 5,
    ) -> list[Suggestion]:
        """Return suggestions for `word`, same Suggestion type as the client."""
        try:
            rows = self._impl.suggest(word, max_suggestions)
        except self._module.KotoshuNativeError as exc:
            raise KotoshuError(f"native suggest failed: {exc}") from exc
        return [Suggestion(**row) for row in rows]


class NativeBackend:
    """Facade over the kotoshu_native extension module.

    Constructing one without the wheel raises NativeUnavailableError
    with instructions (see the module docstring and README).
    """

    def __init__(self) -> None:
        self._module = _required_module()

    @property
    def VERSION(self) -> str:
        """The kotoshu_native module version string."""
        return self._module.VERSION

    @staticmethod
    def available() -> bool:
        """Return True when the kotoshu_native extension module is importable."""
        return available()

    def dictionary(self, aff_path: str, dic_path: str) -> Dictionary:
        """Load Hunspell .aff/.dic files into a native Dictionary."""
        return _load_via(self._module, aff_path, dic_path)


def dictionary(aff_path: str, dic_path: str) -> Dictionary:
    """Load a native dictionary; the offline spell-check entry point.

    Convenience for ``NativeBackend().dictionary(...)``; raises
    NativeUnavailableError when the wheel is not importable.
    """
    return NativeBackend().dictionary(aff_path, dic_path)


# ---- Internals ----


def _required_module() -> ModuleType:
    if _native is None:
        raise NativeUnavailableError(_UNAVAILABLE_MESSAGE)
    return _native


def _load_via(module: ModuleType, aff_path: str, dic_path: str) -> Dictionary:
    try:
        impl = module.Dictionary.load(aff_path, dic_path)
    except module.KotoshuNativeError as exc:
        raise KotoshuError(f"loading native dictionary failed: {exc}") from exc
    return Dictionary(module, impl)


__all__ = [
    "AUTO",
    "ENV_VAR",
    "HTTP",
    "NATIVE",
    "Dictionary",
    "NativeBackend",
    "NativeUnavailableError",
    "available",
    "backend",
    "dictionary",
    "resolve_backend",
]
