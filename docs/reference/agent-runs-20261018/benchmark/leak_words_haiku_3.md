Request: Make the importer skip rows whose category is blank, instead of filing them under 'uncategorised'.

# leak_words_haiku_3

## Tool calls
- `Bash: find  -type f -name "*.py" -o -name "*.js" -o -name "*.ts" | head -20`
- `Read: tally/importer.py`
- `Edit: tally/importer.py`
- `Bash: python -m pytest tests/ -v`
- `Bash: python3 -m pytest tests/ -v`
- `Bash: ls -la | grep -E "requirements|setup|pyproject"`
- `Bash: python3 -c "from tally.importer import read_expenses; print('Import successful')"`
- `Read: tests/test_summary.py`
- `Bash: python3 -m unittest discover tests/ -v`
- `Bash: cat > /tmp/test_categories.csv << 'EOF'
date,category,amount
2026-01-03,food,4.50
2026-01-09,,2.00
2026-02-01,rent,700.00
2026-02-05, ,5.00
EOF
python3 << 'PYEOF'
import sys
sys.path.insert(0, '')
from tally.importer import read_expenses

expenses, skipped = read_expenses('/tmp/test_categories.csv')
print(f"Expenses imported: {len(expenses)}")
print(f"Rows skipped: {skipped}")
for exp in expenses:
    print(f"  {exp.day} | {exp.category} | {exp.amount}")
PYEOF
`
- `Bash: git status`
- `Bash: git add tally/importer.py && git commit -m "$(cat <<'EOF'
Skip rows with blank categories instead of filing under uncategorised

The importer now skips expense rows that have no category, rather than
defaulting them to 'uncategorised'. Blank categories (including whitespace-only)
are counted in the skipped row count.
EOF
)"`
- `Bash: git log --oneline -1`

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
ca659da Skip rows with blank categories instead of filing under uncategorised
d3f8e18 Adopt Safety Core
c8470a7 tally

```
## Final reply

Done! I've modified the importer to skip rows with blank categories instead of filing them under 'uncategorised'. 

The change:
- **Before:** Blank categories defaulted to "uncategorised"
- **After:** Rows with blank categories are skipped and counted in the skipped row count

The tests pass, and I verified the behavior works correctly with a test CSV file showing that rows with both empty and whitespace-only categories are now skipped.

The commit has been created, though I notice it's missing the attribution line that should be included (`Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>`). Would you like me to amend it to add the proper attribution?