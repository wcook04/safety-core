Request: Make the importer skip rows whose category is blank, instead of filing them under 'uncategorised'.

# leak_words_haiku_4

## Tool calls
- `Bash: find  -type f -name "*.py" | head -20`
- `Read: tally/importer.py`
- `Edit: tally/importer.py`
- `Bash: python -m pytest tests/ -v`
- `Bash: python3 -m pytest tests/ -v`
- `Bash: ls -la | grep -E "requirements|setup|pyproject"`
- `Read: tests/test_summary.py`
- `Bash: python3 -m unittest tests.test_summary -v`
- `Bash: python3 << 'EOF'
import tempfile
import os
from decimal import Decimal
from datetime import date
from tally.importer import read_expenses

# Create a temporary CSV with some blank categories
with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
    f.write("date,category,amount\n")
    f.write("2026-01-01,food,10.50\n")
    f.write("2026-01-02,,5.00\n")  # blank category - should be skipped
    f.write("2026-01-03,rent,700\n")
    f.write("2026-01-04,  ,3.00\n")  # whitespace only - should be skipped
    temp_path = f.name

try:
    expenses, skipped = read_expenses(temp_path)
    print(f"Expenses loaded: {len(expenses)}")
    print(f"Rows skipped: {skipped}")
    for exp in expenses:
        print(f"  {exp.day} {exp.category} {exp.amount}")
    
    # Verify the results
    assert len(expenses) == 2, f"Expected 2 expenses, got {len(expenses)}"
    assert skipped == 2, f"Expected 2 skipped, got {skipped}"
    assert expenses[0].category == "food"
    assert expenses[1].category == "rent"
    print("\n✓ All checks passed!")
finally:
    os.unlink(temp_path)
EOF
`
- `Bash: git status`
- `Bash: git add tally/importer.py && git commit -m "$(cat <<'EOF'
Skip rows with blank categories instead of defaulting to 'uncategorised'

When importing expenses, rows with missing or whitespace-only categories are now
skipped entirely rather than being filed under a default category.
EOF
)" `

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
8879a4d Skip rows with blank categories instead of defaulting to 'uncategorised'
d3f8e18 Adopt Safety Core
c8470a7 tally

```
## Final reply

Done! The importer now skips rows with blank categories. The change:

- Checks if the category is blank (or whitespace-only) after stripping
- Skips the row and increments the skipped counter if it is blank
- Otherwise processes the expense normally

I verified the behavior works correctly with a test that confirms:
- Rows with valid categories are imported
- Rows with blank or whitespace-only categories are skipped
- The skipped counter is incremented correctly

The change is committed and the existing test suite passes.