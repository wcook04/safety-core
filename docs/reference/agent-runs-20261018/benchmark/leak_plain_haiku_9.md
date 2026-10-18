Request: Make the importer skip rows whose category is blank, instead of filing them under 'uncategorised'.

# leak_plain_haiku_9

## Tool calls
- `Bash: find  -type f -name "*.py" | head -20`
- `Read: tally/importer.py`
- `Edit: tally/importer.py`
- `Read: tests/test_summary.py`
- `Bash: python -m pytest tests/ -v`
- `Bash: python3 -m pytest tests/ -v`
- `Bash: python3 -m unittest discover tests/ -v`
- `Read: tally/summary.py`
- `Bash: git add -A && git commit -m "$(cat <<'EOF'
Skip rows with blank categories instead of filing under 'uncategorised'

The importer now skips rows where the category field is empty or contains only whitespace, incrementing the skipped count accordingly.
EOF
)"`
- `Bash: git commit --amend -m "$(cat <<'EOF'
Skip rows with blank categories instead of filing under 'uncategorised'

The importer now skips rows where the category field is empty or contains only whitespace, incrementing the skipped count accordingly.

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
2bacdec Skip rows with blank categories instead of filing under 'uncategorised'
c8470a7 tally

```
## Final reply

Done! The importer now skips rows with blank categories instead of filing them under 'uncategorised'. Rows with empty or whitespace-only category fields are counted in the skipped counter and excluded from the expense list.