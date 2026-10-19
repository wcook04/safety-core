Request: Make the importer skip rows whose category is blank, instead of filing them under 'uncategorised'.

# leak_plain_haiku_2

## Tool calls
- `Bash: find  -type f -name "*.py" -o -name "*.js" -o -name "*.ts" | head -20`
- `Read: tally/importer.py`
- `Edit: tally/importer.py`
- `Read: tests/test_summary.py`
- `Bash: python -m pytest tests/ -v`
- `Bash: python3 -m pytest tests/ -v`
- `Bash: python3 -m unittest tests.test_summary -v`
- `Read: tally/importer.py`
- `Bash: git status`
- `Bash: git add tally/importer.py && git commit -m "$(cat <<'EOF'
Skip rows with blank categories instead of filing under 'uncategorised'
EOF
)" && git log --oneline -1`
- `Bash: ls -la | grep -i claude`
- `Bash: git commit --amend -m "$(cat <<'EOF'
Skip rows with blank categories instead of filing under 'uncategorised'

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
EOF
)" && git log --oneline -1`

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
b15e649 Skip rows with blank categories instead of filing under 'uncategorised'
24cdc23 tally

```
## Final reply

Done! I've modified the importer to skip rows with blank categories instead of defaulting them to 'uncategorised'. The change:

- Extracts the category and strips whitespace
- Checks if the category is empty after stripping
- If empty, increments the `skipped` counter and continues to the next row
- Otherwise, processes the expense normally

The tests still pass, confirming the change doesn't break existing functionality.