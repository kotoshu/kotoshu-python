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

## License

BSD-2-Clause, same as Kotoshu.
