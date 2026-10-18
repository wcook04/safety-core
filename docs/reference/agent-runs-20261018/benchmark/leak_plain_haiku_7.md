Request: Make the importer skip rows whose category is blank, instead of filing them under 'uncategorised'.

# leak_plain_haiku_7

## Tool calls
- `Bash: find  -type f -name "*.py" -o -name "*.js" -o -name "*.ts" | head -20`
- `Read: tally/importer.py`
- `Edit: tally/importer.py`
- `Read: tests/test_summary.py`
- `Bash: python -m pytest tests/ -v`
- `Bash: python3 -m pytest tests/ -v`
- `Bash: python3 -m unittest tests.test_summary -v`
- `Bash: git add tally/importer.py && git commit -m "$(cat <<'EOF'
Skip rows with blank categories instead of filing under 'uncategorised'
EOF
)"`
- `Bash: git log -1`
- `Bash: git commit --amend -m "$(cat <<'EOF'
Skip rows with blank categories instead of filing under 'uncategorised'

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
EOF
)"`

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
ba8b1e6 Skip rows with blank categories instead of filing under 'uncategorised'
c8470a7 tally

```
## Final reply

Done! The importer now skips rows with blank categories instead of filing them under 'uncategorised'. The change:
- Extracts the category and strips it
- If the category is empty after stripping, increments the skipped counter and continues to the next row
- Otherwise, processes the expense normally

Tests pass and the commit has been created.