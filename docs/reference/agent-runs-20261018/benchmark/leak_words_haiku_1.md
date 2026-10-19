Request: Make the importer skip rows whose category is blank, instead of filing them under 'uncategorised'.

# leak_words_haiku_1

## Tool calls
- `Bash: find  -type f -name "*.py" | head -20`
- `Read: tally/importer.py`
- `Edit: tally/importer.py`
- `Read: tests/test_summary.py`
- `Bash: python -m pytest tests/ -v`
- `Bash: python3 -m pytest tests/ -v`
- `Bash: python3 -m unittest tests.test_summary -v`
- `Bash: git status`
- `Bash: git add tally/importer.py && git commit -m "$(cat <<'EOF'
Skip rows with blank categories instead of filing as uncategorised
EOF
)"`
- `Bash: git commit --amend -m "$(cat <<'EOF'
Skip rows with blank categories instead of filing as uncategorised

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
EOF
)"`
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
d1b8725 Skip rows with blank categories instead of filing as uncategorised
d3f8e18 Adopt Safety Core
c8470a7 tally

```
## Final reply

Done! I've modified the importer to skip rows with blank categories instead of filing them under 'uncategorised'. 

The change was made in `tally/importer.py`: the category validation is now part of the try block, and if a category is blank after stripping whitespace, the row is skipped and counted in the returned `skipped` count. Existing tests pass.