"""Command-line entry point: print a summary table to the terminal."""

import argparse

from tally.importer import read_expenses
from tally.summary import totals_by_category, totals_by_month


def build_parser():
    parser = argparse.ArgumentParser(prog="tally", description="Summarise expenses from a CSV file.")
    parser.add_argument("csv_path", help="CSV file with date, category and amount columns")
    parser.add_argument("--by", choices=["category", "month"], default="category",
                        help="group totals by category (default) or by month")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    expenses, skipped = read_expenses(args.csv_path)
    totals = totals_by_month(expenses) if args.by == "month" else totals_by_category(expenses)
    width = max((len(key) for key in totals), default=0)
    for key, amount in totals.items():
        print(f"{key.ljust(width)}  {amount:>10.2f}")
    print(f"{'total'.ljust(width)}  {sum(totals.values()):>10.2f}")
    if skipped:
        print(f"skipped {skipped} row(s) with a missing or unreadable amount or date")
    return 0
