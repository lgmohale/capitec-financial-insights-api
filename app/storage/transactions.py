import random
from collections import Counter
from datetime import date, timedelta
from uuid import UUID

from app.storage.object_storage import read_json_object, upload_json_object

MIN_HISTORY_WEEKS = 14
MIN_TRANSACTIONS_PER_WEEK = 7

STARTER_TRANSACTIONS = [
    {
        "id": "txn-001",
        "date": "2026-04-25",
        "type": "credit",
        "description": "SALARY PAYMENT EMPLOYER",
        "amount": 46579.0,
        "currency": "ZAR",
        "balance": 46579.0,
        "merchant": "Employer",
    },
    {
        "id": "txn-002",
        "date": "2026-04-26",
        "type": "debit",
        "description": "CHECKERS HYPER GROCERIES",
        "amount": -1240.5,
        "currency": "ZAR",
        "balance": 45338.5,
        "merchant": "Checkers",
    },
    {
        "id": "txn-003",
        "date": "2026-04-27",
        "type": "debit",
        "description": "SHELL GARAGE FUEL",
        "amount": -850.0,
        "currency": "ZAR",
        "balance": 44488.5,
        "merchant": "Shell",
    },
    {
        "id": "txn-004",
        "date": "2026-04-28",
        "type": "debit",
        "description": "HOME LOAN REPAYMENT",
        "amount": -13200.0,
        "currency": "ZAR",
        "balance": 31288.5,
        "merchant": "FNB Home Loan",
    },
    {
        "id": "txn-005",
        "date": "2026-04-29",
        "type": "debit",
        "description": "HOLLYWOODBETS ONLINE",
        "amount": -500.0,
        "currency": "ZAR",
        "balance": 30788.5,
        "merchant": "Hollywoodbets",
    },
]

DEBIT_TEMPLATES = [
    ("CHECKERS HYPER GROCERIES", "Checkers", -250.0, -2400.0),
    ("SHELL GARAGE FUEL", "Shell", -450.0, -1400.0),
    ("HOME LOAN REPAYMENT", "FNB Home Loan", -9000.0, -16500.0),
    ("NETFLIX SUBSCRIPTION", "Netflix", -120.0, -250.0),
    ("ELECTRICITY PREPAID", "Municipality", -350.0, -1800.0),
    ("BANK SERVICE FEE", "Capitec", -45.0, -150.0),
    ("HOLLYWOODBETS ONLINE", "Hollywoodbets", -100.0, -750.0),
    ("SCHOOL FEES PAYMENT", "School", -800.0, -3500.0),
    ("INSURANCE PREMIUM", "Insurance Provider", -300.0, -1800.0),
    ("PERSONAL LOAN REPAYMENT", "Loan Provider", -700.0, -3200.0),
]

CREDIT_TEMPLATES = [
    ("EFT TRANSFER RECEIVED", "Transfer", 250.0, 2500.0),
    ("CASH DEPOSIT", "Cash Deposit", 100.0, 1800.0),
    ("REFUND RECEIVED", "Refund", 80.0, 950.0),
]


def transaction_object_key(bank_statement_id: UUID) -> str:
    return f"output/{bank_statement_id}/transactions.json"


def processed_output_object_key(bank_statement_id: UUID, output_name: str) -> str:
    return f"output/{bank_statement_id}/{output_name}.json"


def write_starter_transactions(bank_statement_id: UUID) -> str:
    transactions = generate_random_transaction_history()
    return upload_json_object(
        object_key=transaction_object_key(bank_statement_id),
        value=transactions,
    )


def read_starter_transactions(bank_statement_id: UUID) -> list[dict]:
    return read_json_object(transaction_object_key(bank_statement_id))


def generate_random_transaction_history() -> list[dict]:
    today = date.today()
    start_date = today - timedelta(weeks=MIN_HISTORY_WEEKS, days=7)
    transactions = []

    for week_number in range(MIN_HISTORY_WEEKS):
        week_start = start_date + timedelta(weeks=week_number)
        for day_offset in range(MIN_TRANSACTIONS_PER_WEEK):
            transaction_date = week_start + timedelta(days=day_offset)
            transactions.append(build_random_transaction(transaction_date))

    for salary_date in get_salary_dates(start_date, today):
        transactions.append(
            {
                "date": salary_date.isoformat(),
                "type": "credit",
                "description": "SALARY PAYMENT EMPLOYER",
                "amount": round(random.uniform(28000.0, 52000.0), 2),
                "currency": "ZAR",
                "merchant": "Employer",
            }
        )

    transactions = ensure_weekly_minimum(transactions, start_date)
    transactions.sort(key=lambda transaction: transaction["date"])
    return add_ids_and_balances(transactions)


def build_random_transaction(transaction_date: date) -> dict:
    templates = CREDIT_TEMPLATES if random.random() < 0.18 else DEBIT_TEMPLATES
    description, merchant, min_amount, max_amount = random.choice(templates)
    amount = round(random.uniform(min_amount, max_amount), 2)
    transaction_type = "credit" if amount > 0 else "debit"

    return {
        "date": transaction_date.isoformat(),
        "type": transaction_type,
        "description": description,
        "amount": amount,
        "currency": "ZAR",
        "merchant": merchant,
    }


def get_salary_dates(start_date: date, end_date: date) -> list[date]:
    salary_dates = []
    current = date(start_date.year, start_date.month, 25)
    if current < start_date:
        current = add_month(current)

    while current <= end_date:
        salary_dates.append(current)
        current = add_month(current)

    return salary_dates


def add_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, value.day)
    return date(value.year, value.month + 1, value.day)


def ensure_weekly_minimum(transactions: list[dict], start_date: date) -> list[dict]:
    weekly_counts = Counter(
        (date.fromisoformat(transaction["date"]) - start_date).days // 7
        for transaction in transactions
    )

    for week_number in range(MIN_HISTORY_WEEKS):
        missing_count = MIN_TRANSACTIONS_PER_WEEK - weekly_counts[week_number]
        week_start = start_date + timedelta(weeks=week_number)
        for _ in range(max(missing_count, 0)):
            transaction_date = week_start + timedelta(days=random.randint(0, 6))
            transactions.append(build_random_transaction(transaction_date))

    return transactions


def add_ids_and_balances(transactions: list[dict]) -> list[dict]:
    balance = round(random.uniform(2500.0, 10000.0), 2)
    completed_transactions = []

    for index, transaction in enumerate(transactions, start=1):
        amount = float(transaction["amount"])
        balance = round(balance + amount, 2)
        completed_transactions.append(
            {
                "id": f"txn-{index:03d}",
                "date": transaction["date"],
                "type": transaction["type"],
                "description": transaction["description"],
                "amount": amount,
                "currency": transaction["currency"],
                "balance": balance,
                "merchant": transaction["merchant"],
            }
        )

    return completed_transactions
