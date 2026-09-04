# kotoshu-python

Python client for the [Kotoshu](https://github.com/kotoshu/kotoshu) HTTP
spell-check API.

## Install

```bash
pip install kotoshu
```

## Quick start

```python
from kotoshu import Client

client = Client("http://localhost:9292")

# Check a document
result = client.check("helo wrold", language="en")
for err in result.errors:
    print(f"{err.word} -> {err.top_suggestions}")

# Suggestions for one word
for sug in client.suggest("helo", max_suggestions=3):
    print(sug.word, sug.confidence)

# Language detection
det = client.detect("bonjour le monde")
print(det.language, det.confidence)
```

## Reference

### `Client(base_url, *, language="en", timeout=30.0, session=None)`

- `health() -> dict`
- `languages() -> list[str]`
- `check(text, *, language=None, fmt="full") -> DocumentResult`
- `suggest(word, *, language=None, max_suggestions=None) -> list[Suggestion]`
- `detect(text) -> Detection`
- `correct(word, *, language=None) -> bool`

### Result types

- `DocumentResult`: `file`, `word_count`, `errors: list[WordError]`, `success`, `misspelled_words`
- `WordError`: `word`, `position`, `suggestions: list[Suggestion]`, `top_suggestions`
- `Suggestion`: `word`, `distance`, `confidence`, `source`, `metadata`
- `Detection`: `language`, `confidence`

### Exceptions

- `KotoshuError`: base
- `ResourceNotSetupError`: server returned 422 — language not set up

## Native backend (optional, offline)

`kotoshu` can also spell-check fully offline through the native Rust
engine instead of the HTTP API. The engine ships in the
[`kotoshu-native`](https://github.com/kotoshu/kotoshu-rs) wheel (module
`kotoshu_native`) and works on local Hunspell dictionaries:

```python
from kotoshu.native import dictionary

d = dictionary("en_US.aff", "en_US.dic")
d.correct("hello")                      # True
d.suggest("hlelo", max_suggestions=3)   # [Suggestion(word="hello", ...)]
```

`Dictionary.correct`/`suggest` return exactly the same types as the HTTP
`Client` (`bool` and `list[Suggestion]`), so result handling is identical
across backends. The offline engine is word-level only: no document
parsing, no language detection.

### `KOTOSHU_BACKEND`

- `auto` (default): native when `kotoshu_native` is importable, else HTTP
- `native`: require the native engine (`NativeUnavailableError` when missing)
- `http`: always the HTTP API

`kotoshu.backend()` reports the backend in effect (`"native"` or
`"http"`); `kotoshu.native.available()` whether the wheel is importable.

### Getting the wheel

The `kotoshu-native` wheel is **not published to PyPI yet** (publishing
is blocked on owner credentials), so `pip install kotoshu[native]`
resolves only after that first publish. Until then build it locally from
the [kotoshu-rs](https://github.com/kotoshu/kotoshu-rs) repository:

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install maturin
cd /path/to/kotoshu-rs/kotoshu-python
maturin develop
```

Without the wheel nothing changes: `auto` silently uses HTTP and the
client behaves exactly as before.

## License

BSD-2-Clause, same as Kotoshu.
