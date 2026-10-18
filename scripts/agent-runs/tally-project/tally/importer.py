"""Read expense rows from a CSV file."""

import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class Expense:
    day: date
    category: str
    amount: Decimal


def read_expenses(path):
    """Return (expenses, skipped) from a CSV with date, category, amount columns."""
    expenses = []
    skipped = 0
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            try:
                amount = Decimal(row["amount"].strip())
                day = date.fromisoformat(row["date"].strip())
            except (KeyError, AttributeError, InvalidOperation, ValueError):
                skipped += 1
                continue
            category = (row.get("category") or "uncategorised").strip().lower()
            expenses.append(Expense(day, category, amount))
    return expenses, skipped
