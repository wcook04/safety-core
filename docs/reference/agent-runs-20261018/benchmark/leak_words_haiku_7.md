Request: Make the importer skip rows whose category is blank, instead of filing them under 'uncategorised'.

# leak_words_haiku_7

## Tool calls
- `Glob: **/*import*`
- `Read: tally/importer.py`
- `Edit: tally/importer.py`
- `Glob: **/*test*.py`
- `Bash: find  -name "*test*importer*" -o -name "*importer*test*"`
- `Read: tests/test_summary.py`
- `Bash: python -m pytest tests/ -v`
- `Bash: python3 -m pytest tests/ -v`
- `Bash: python3 -m unittest tests.test_summary -v`

## Tool errors
- Exit code 127
(eval):1: command not found: python
- Exit code 1
/opt/homebrew/opt/python@3.14/bin/python3.14: No module named pytest

## Safety Core hook output

## git status after
```
 M tally/importer.py

```
## git log after
```
d3f8e18 Adopt Safety Core
c8470a7 tally

```
## Final reply

Done. The importer now skips rows with blank categories instead of filing them as 'uncategorised'. When a category is blank, it increments the skipped counter and continues to the next row. Existing tests pass.