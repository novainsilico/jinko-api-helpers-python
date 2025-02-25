## Test

```
poetry run pytest tests
```

## Regenerate the sdk

Run this from a valid poetry environment:

```sh
just sdk
```

## Lint

```
poetry run black .
```

## Docs

```
poetry run python -m pydoc -p 0 jinko_helpers
```

## Update changelog

Add an entry at the top of the CHANGELOG.md file.

