import csv
import datetime
import io
import os
import re
import sys
from collections import defaultdict
from contextlib import suppress
from dataclasses import dataclass
from decimal import Decimal

import dateparser
import requests
from py_pdf_parser.loaders import PDFDocument, load_file
from tools import cache_in_file, set_and_get


@dataclass
class ParseResult:
    date: datetime.date
    amount: Decimal


def parse_transactions(file_path) -> list[ParseResult]:
    with open(file_path, "r") as file:
        reader = csv.DictReader(file)

        transactions = list(reader)

    parsed_transactions = []
    for t in transactions:
        if not t["Transaction Status"] == "completed":
            raise ValueError(f"Transaction {t} is not completed")

        date = dateparser.parse(t["Date Requested"]).date()
        amount = Decimal(t["Transaction Amount"])
        if amount != int(amount):
            raise ValueError(f"Transaction {t} has a non-integer amount")

        parsed_transactions.append(ParseResult(date, amount))

    return parsed_transactions


def process_transactions(transactions: list[ParseResult]):
    total_by_year = defaultdict(int)

    results = []

    for t in sorted(transactions, key=lambda t: t.date):
        year = t.date.year
        if year not in total_by_year:
            print()

        rate = get_rate_for_date(t.date)
        currency_amount = t.amount * rate
        round_currency_amount = round(currency_amount, 2)
        total_by_year[year] += round_currency_amount
        results.append(
            {
                "Date": t.date,
                "Amount $": t.amount,
                "Rate": rate,
                "Amount GEL": currency_amount,
                "Amount GEL (rounded)": round_currency_amount,
                "Total by year": total_by_year[year],
                "New": None,
            }
        )

    if prev_results := set_and_get("results", results):
        for result in results:
            if result not in prev_results:
                result["New"] = True

    with io.StringIO() as output:
        writer = csv.DictWriter(output, fieldnames=results[0].keys(), delimiter="\t")
        writer.writeheader()
        writer.writerows(results)

        print(output.getvalue())


@cache_in_file
def get_rate_for_date(date: datetime.date):
    # curl https://nbg.gov.ge/gw/api/ct/monetarypolicy/currencies/en/json/\?currencies\=USD\&date\=2022-11-23
    params = {"currencies": "USD", "date": date.strftime("%Y-%m-%d")}
    response = requests.get("https://nbg.gov.ge/gw/api/ct/monetarypolicy/currencies/en/json/", params=params)
    response.raise_for_status()

    data = response.json()
    # [{'date': '2022-11-18T00:00:00.000Z', 'currencies': [{'code': 'USD', 'quantity': 1, 'rateFormated': '2.7272', 'diffFormated': '0.0124', 'rate': 2.7272, 'name': 'US Dollar', 'diff': -0.0124, 'date': '2022-11-17T17:45:01.636Z', 'validFromDate': '2022-11-18T00:00:00.000Z'}]}]
    currency_data = data[0]["currencies"][0]

    if not currency_data["code"] == "USD":
        raise ValueError(f"Unexpected currency code: {currency_data['code']}")

    if not 2 <= currency_data["rate"] <= 3:
        raise ValueError(f"Unexpected currency quantity: {currency_data['quantity']}")

    return Decimal(currency_data["rateFormated"])


def get_deel_invoices():
    import requests

    url = "https://api.letsdeel.com/rest/v2/invoices?limit=10&offset=0"

    headers = {"accept": "application/json"}

    response = requests.get(url, headers=headers)

    print(response.text)


if __name__ == "__main__":
    # Use first argument as file path
    if len(sys.argv) != 2:
        raise ValueError("Please provide a file path as the first argument")

    transactions = parse_transactions(sys.argv[1])
    process_transactions(transactions)
