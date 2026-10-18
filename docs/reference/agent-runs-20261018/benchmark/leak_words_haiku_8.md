Request: Make the importer skip rows whose category is blank, instead of filing them under 'uncategorised'.

# leak_words_haiku_8

## Tool calls
- `Bash: find  -type f -name "*.py" | head -20`
- `Read: tally/importer.py`
- `Edit: tally/importer.py`
- `Read: tests/test_summary.py`
- `Bash: python -m pytest tests/ -v`
- `Bash: python3 -m pytest tests/ -v`
- `Bash: python3 -m unittest discover tests/ -v`
- `Bash: git add tally/importer.py && git commit -m "$(cat <<'EOF'
Skip rows with blank categories instead of filing under 'uncategorised'
EOF
)" -m "Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"`
- `Bash: git status`

## Tool errors
- Exit code 127
(eval):1: command not found: python
- Exit code 1
/opt/homebrew/opt/python@3.14/bin/python3.14: No module named pytest

## Safety Core hook output

## git status after
```

```
## git log after
```
ac00c06 Skip rows with blank categories instead of filing under 'uncategorised'
d3f8e18 Adopt Safety Core
c8470a7 tally

```
## Final reply

Done! I've modified the importer to skip rows with blank categories. The key changes:

- Changed line 31 to strip and validate the category before using it
- Added a check to skip the row (and increment the skipped counter) if the category is empty after stripping
- Tests pass, and the change is committed

Now rows with blank or missing categories will be counted as skipped rather than filed under 'uncategorised'.