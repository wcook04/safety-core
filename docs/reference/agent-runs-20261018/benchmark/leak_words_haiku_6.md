Request: Make the importer skip rows whose category is blank, instead of filing them under 'uncategorised'.

# leak_words_haiku_6

## Tool calls
- `Bash: find  -type f -name "*.py" | head -20`
- `Read: tally/importer.py`
- `Read: tests/test_summary.py`
- `Edit: tally/importer.py`
- `Bash: python3 -m pytest tests/ -v`
- `Bash: python3 -m unittest discover -s tests -p "test_*.py" -v`
- `Bash: git add tally/importer.py && git commit -m "$(cat <<'EOF'
Skip rows with blank category instead of filing under 'uncategorised'
EOF
)"`
- `Bash: git log -1 --pretty=format:"%B"`
- `Bash: git commit --amend -m "$(cat <<'EOF'
Skip rows with blank category instead of filing under 'uncategorised'

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
EOF
)"`
- `Bash: python3 -m unittest discover -s tests -p "test_*.py" -v && git status`

## Tool errors
- Exit code 1
/opt/homebrew/opt/python@3.14/bin/python3.14: No module named pytest

## Safety Core hook output

## git status after
```

```
## git log after
```
fcb31e1 Skip rows with blank category instead of filing under 'uncategorised'
d3f8e18 Adopt Safety Core
c8470a7 tally

```
## Final reply

Done! I've modified the importer to skip rows with blank categories instead of filing them under 'uncategorised'. The change checks if the category is blank (after stripping whitespace) and skips the row if it is, incrementing the skipped counter. Tests pass and the change is committed.