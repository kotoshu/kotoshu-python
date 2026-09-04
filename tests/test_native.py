"""Native backend selection and wrapper tests (no network, no wheel).

The kotoshu_native extension module is not installed in this venv (the
wheel awaits its first PyPI publish), so import success is simulated with
a real in-memory module object implementing the documented surface; the
selection logic itself is exercised through its pure function with plain
strings and bools.
"""
import types

import pytest

import kotoshu
from kotoshu import Suggestion
from kotoshu import native as k_native
from kotoshu.native import Dictionary, NativeBackend, NativeUnavailableError, resolve_backend

# The frozen conformance row every backend must agree on.
HELLO_ROW = {"word": "hello", "distance": 1, "confidence": 1.0, "source": "edit_distance"}


def make_fake_module(*, fail_load=False, fail_ops=False):
    """A real in-memory stand-in for the kotoshu_native extension module."""
    module = types.ModuleType("kotoshu_native")
    module.VERSION = "0.0.0-test"

    class KotoshuNativeError(Exception):
        pass

    class Engine:
        def correct(self, word):
            if fail_ops:
                raise KotoshuNativeError("engine boom")
            return word == "hello"

        def suggest(self, word, limit=5):
            if fail_ops:
                raise KotoshuNativeError("engine boom")
            rows = [HELLO_ROW, {"word": "shells", "distance": 3, "confidence": 0.2, "source": "ngram"}]
            return rows[:limit]

    def load(aff_path, dic_path):
        if fail_load:
            raise KotoshuNativeError(f"cannot open {aff_path}")
        return Engine()

    module.KotoshuNativeError = KotoshuNativeError
    module.Dictionary = types.SimpleNamespace(load=load)
    return module


@pytest.fixture
def no_native(monkeypatch):
    """Simulate the wheel being missing (the failed-import state)."""
    monkeypatch.setattr(k_native, "_native", None)


@pytest.fixture
def fake_native(monkeypatch):
    """Simulate the wheel being installed."""
    module = make_fake_module()
    monkeypatch.setattr(k_native, "_native", module)
    return module


# ---- Availability ----


def test_available_false_without_wheel(no_native):
    assert k_native.available() is False
    assert NativeBackend.available() is False


def test_available_true_with_module(fake_native):
    assert k_native.available() is True
    assert NativeBackend.available() is True


def test_native_unavailable_error_is_kotoshu_error():
    assert issubclass(NativeUnavailableError, kotoshu.KotoshuError)


# ---- Backend selection (pure decision function) ----


@pytest.mark.parametrize(
    "setting, is_available, expected",
    [
        ("auto", True, "native"),
        ("auto", False, "http"),
        (None, True, "native"),
        (None, False, "http"),
        ("", False, "http"),
        ("  Native ", True, "native"),
        ("HTTP", False, "http"),
        ("http", True, "http"),
        ("native", True, "native"),
    ],
)
def test_resolve_backend_matrix(setting, is_available, expected):
    assert resolve_backend(setting, is_available) == expected


def test_resolve_backend_forced_native_missing_raises():
    with pytest.raises(NativeUnavailableError) as excinfo:
        resolve_backend("native", False)
    message = str(excinfo.value)
    assert "PyPI" in message
    assert "maturin develop" in message


def test_resolve_backend_invalid_value():
    with pytest.raises(ValueError, match="KOTOSHU_BACKEND"):
        resolve_backend("bogus", True)


# ---- backend() reads the environment ----


def test_backend_auto_falls_back_to_http(no_native, monkeypatch):
    monkeypatch.delenv(k_native.ENV_VAR, raising=False)
    assert kotoshu.backend() == "http"


def test_backend_auto_prefers_native(fake_native, monkeypatch):
    monkeypatch.delenv(k_native.ENV_VAR, raising=False)
    assert kotoshu.backend() == "native"


def test_backend_http_forced(fake_native, monkeypatch):
    monkeypatch.setenv(k_native.ENV_VAR, "http")
    assert kotoshu.backend() == "http"


def test_backend_native_forced_but_unavailable(no_native, monkeypatch):
    monkeypatch.setenv(k_native.ENV_VAR, "native")
    with pytest.raises(NativeUnavailableError) as excinfo:
        kotoshu.backend()
    assert "PyPI" in str(excinfo.value)
    assert "maturin develop" in str(excinfo.value)


def test_backend_invalid_env(fake_native, monkeypatch):
    monkeypatch.setenv(k_native.ENV_VAR, "grpc")
    with pytest.raises(ValueError):
        kotoshu.backend()


# ---- The Dictionary wrapper ----


def test_dictionary_shapes_match_http_client(fake_native):
    d = k_native.dictionary("en_US.aff", "en_US.dic")
    assert isinstance(d, Dictionary)
    assert d.correct("hello") is True
    assert d.correct("hlelo") is False
    assert d.suggest("hlelo", max_suggestions=3) == [
        Suggestion(**HELLO_ROW),
        Suggestion(word="shells", distance=3, confidence=0.2, source="ngram"),
    ]


def test_dictionary_suggest_default_limit(fake_native):
    d = Dictionary.load("en_US.aff", "en_US.dic")
    assert len(d.suggest("hlelo")) == 2
    assert len(d.suggest("hlelo", max_suggestions=1)) == 1


def test_dictionary_version_exposed(fake_native):
    assert NativeBackend().VERSION == "0.0.0-test"


def test_native_backend_unavailable_without_wheel(no_native):
    with pytest.raises(NativeUnavailableError, match="maturin develop"):
        NativeBackend()
    with pytest.raises(NativeUnavailableError, match="maturin develop"):
        k_native.dictionary("en_US.aff", "en_US.dic")


def test_dictionary_load_failure_wrapped(monkeypatch):
    monkeypatch.setattr(k_native, "_native", make_fake_module(fail_load=True))
    with pytest.raises(kotoshu.KotoshuError, match="cannot open") as excinfo:
        k_native.dictionary("bad.aff", "bad.dic")
    assert not isinstance(excinfo.value, NativeUnavailableError)


def test_dictionary_operation_failure_wrapped(monkeypatch):
    monkeypatch.setattr(k_native, "_native", make_fake_module(fail_ops=False))
    d = k_native.dictionary("en_US.aff", "en_US.dic")
    monkeypatch.setattr(k_native, "_native", make_fake_module(fail_ops=True))
    broken = k_native.dictionary("en_US.aff", "en_US.dic")
    with pytest.raises(kotoshu.KotoshuError, match="engine boom"):
        broken.correct("hello")
    with pytest.raises(kotoshu.KotoshuError, match="engine boom"):
        broken.suggest("hlelo")
    assert d.correct("hello") is True


# ---- The real wheel, when it happens to be importable ----


@pytest.mark.skipif(not k_native.available(), reason="kotoshu_native wheel not installed")
def test_real_module_surface():
    import kotoshu_native

    assert isinstance(kotoshu_native.VERSION, str)
    assert kotoshu_native.available() is True
    assert NativeBackend().VERSION == kotoshu_native.VERSION
