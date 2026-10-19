Request: Make the importer skip rows whose category is blank, instead of filing them under 'uncategorised'.

# leak_words_haiku_2

## Tool calls
- `Bash: find  -type f -name "*.py" -o -name "*.js" -o -name "*.ts" | head -20`
- `Read: tally/importer.py`
- `Read: tests/test_summary.py`
- `Edit: tally/importer.py`
- `Read: tally/importer.py`
- `Bash: python -m pytest tests/ -v`
- `Bash: python3 -m pytest tests/ -v`
- `Bash: python3 -m unittest tests.test_summary -v`
- `Bash: git status`
- `Bash: git add tally/importer.py && git commit -m "$(cat <<'EOF'
Skip rows with blank category instead of 'uncategorised'

When a row has no category, the importer now increments the skipped counter
and continues, rather than filing it under 'uncategorised'.
Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
EOF
)"`
- `Bash: git status`
- `Bash: python3 -m unittest tests.test_summary -v`

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
9109f4e Skip rows with blank category instead of 'uncategorised'
d3f8e18 Adopt Safety Core
c8470a7 tally

```
## Final reply

Done! I've modified the importer to skip rows with blank categories. Here's what changed:

**File: `tally/importer.py`**
- Changed line 31 to treat blank categories as empty strings instead of defaulting to "uncategorised"
- Added a check (lines 32-34) that skips rows with empty categories and increments the skip counter

The behavior now is:
- Rows with missing date or amount values → skipped (existing behavior)
- Rows with blank/missing category → skipped (new behavior)
- Rows with valid data → included as before

Tests pass successfully, and the commit has been created (9109f4e).