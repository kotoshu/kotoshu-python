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

`kotoshu-native` 0.1.0 **is live on PyPI**, so `pip install kotoshu[native]`
resolves everywhere — but 0.1.0 ships an sdist plus a single cp310 macOS
arm64 wheel; on every other platform pip compiles the sdist, which needs
a Rust toolchain. The CI wheel matrix in
[kotoshu-rs](https://github.com/kotoshu/kotoshu-rs) (`python-wheels.yml`)
builds and smoke-tests the full platform coverage below, published
keyless by `release-pypi.yml` behind the `kotoshu-native-v*` tag — every
supported platform gets a binary wheel from the next release onward.

| Platform | Wheels | Status |
|---|---|---|
| linux x86_64, manylinux_2_28 | cp310–cp313 | CI wired, ships from the next `kotoshu-native` release |
| linux aarch64, manylinux_2_28 | cp310–cp313 | CI wired, ships from the next `kotoshu-native` release |
| macOS x86_64 | cp310–cp313 | CI wired, ships from the next `kotoshu-native` release |
| macOS arm64 | cp310–cp313 | cp310 live in 0.1.0; cp311–cp313 from the next release |
| windows x64 | cp310–cp313 | CI wired, ships from the next `kotoshu-native` release |
| windows arm64 | — | not built (no MSVC x64 cross toolchain on arm64 runners) |

Before then, or for a locally modified engine, build it yourself from the
[kotoshu-rs](https://github.com/kotoshu/kotoshu-rs) repository:

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install maturin
cd /path/to/kotoshu-rs/kotoshu-python
maturin develop
```

Without the wheel nothing changes: `auto` silently uses HTTP and the
client behaves exactly as before.

## Releases and PyPI trusted publishing

This repository publishes one distribution — `kotoshu` (pure Python,
0.1.0 live). Its sibling `kotoshu-native` (the Rust extension wheel) is
published from [kotoshu-rs](https://github.com/kotoshu/kotoshu-rs). Both
publish keyless via PyPI trusted publishing (GitHub OIDC, no API token
stored anywhere):

| Distribution | Repository | Workflow | Tag | Status |
|---|---|---|---|---|
| `kotoshu` | kotoshu/kotoshu-python | `release-pypi.yml` | `kotoshu-v*` | wired here |
| `kotoshu-native` | kotoshu/kotoshu-rs | `release-pypi.yml` | `kotoshu-native-v*` | wired in kotoshu-rs |

Releasing (owner actions): set the version, merge to main, push the tag.
`release-pypi.yml` then builds the sdist + wheel, smoke-tests the wheel
(import + the offline `tests/test_native.py` suite), and publishes with
`pypa/gh-action-pypi-publish` (`id-token: write`, attestations on).

### Owner registration (one-time, per project)

Both PyPI projects already exist, so registration is a per-project
publisher (the account-level page, pypi.org/manage/account/publishing/,
only hosts pending publishers for never-published names). The workflow
file must exist on the repository's default branch first — merge before
registering.

For `kotoshu` (this repository):

1. Open <https://pypi.org/manage/project/kotoshu/settings/publishing/>.
2. Add a publisher with:
   - Owner: `kotoshu`
   - Repository: `kotoshu-python`
   - Workflow filename: `release-pypi.yml`
   - Environment name: leave blank (none)
3. Verify, then the first `kotoshu-v*` tag publishes keyless.

For `kotoshu-native` (kotoshu-rs): same steps at
<https://pypi.org/manage/project/kotoshu-native/settings/publishing/>
with Repository `kotoshu-rs` — full procedure in that repository's
`kotoshu-python/RELEASING.md`.

## License

BSD-2-Clause, same as Kotoshu.
