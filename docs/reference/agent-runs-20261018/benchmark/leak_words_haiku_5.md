Request: Make the importer skip rows whose category is blank, instead of filing them under 'uncategorised'.

# leak_words_haiku_5

## Tool calls
- `Bash: find  -type f -name "*.py" | head -20`
- `Read: tally/importer.py`
- `Read: tests/test_summary.py`
- `Edit: tally/importer.py`
- `Bash: python -m pytest tests/ -v`
- `Bash: python3 -m pytest tests/ -v`
- `Bash: python3 -m unittest discover tests -v`
- `Bash: git add tally/importer.py && git commit -m "$(cat <<'EOF'
Skip rows with blank category instead of filing under 'uncategorised'

When importing expenses, rows with empty or missing category values are now skipped rather than defaulting to 'uncategorised', keeping the category data cleaner and more intentional.
EOF
)"`
- `Bash: git log -1 --format="%B"`
- `Bash: git commit --amend -m "$(cat <<'EOF'
Skip rows with blank category instead of filing under 'uncategorised'

When importing expenses, rows with empty or missing category values are now skipped rather than defaulting to 'uncategorised', keeping the category data cleaner and more intentional.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
EOF
)"`
- `Bash: git log -1 --format="%B"`
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
c9dbcb6 Skip rows with blank category instead of filing under 'uncategorised'
d3f8e18 Adopt Safety Core
c8470a7 tally

```
## Final reply

Done! I've modified the importer to skip rows with blank categories instead of filing them under 'uncategorised'. Here's what changed:

**Key modification in `tally/importer.py`:**
- Moved category extraction into the try block
- Added a check: if the category is empty after stripping whitespace, the row is skipped and counted in the `skipped` counter
- Rows with missing or blank categories are now properly accounted for as skipped rows

The existing tests pass, and the commit is recorded with full attribution.