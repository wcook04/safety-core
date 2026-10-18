"""Group expenses into totals."""

from collections import defaultdict
from decimal import Decimal


def totals_by_category(expenses):
    totals = defaultdict(Decimal)
    for expense in expenses:
        totals[expense.category] += expense.amount
    return dict(sorted(totals.items()))


def totals_by_month(expenses):
    totals = defaultdict(Decimal)
    for expense in expenses:
        totals[expense.day.strftime("%Y-%m")] += expense.amount
    return dict(sorted(totals.items()))
