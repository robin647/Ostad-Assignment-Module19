# Bank Account Transaction Management System

A secure, server-rendered Django web application for managing bank accounts, deposits, withdrawals, and transaction history. Built with Django, Django Templates, the Django ORM, SQLite, and Bootstrap 5.

## Description

BankEase lets authenticated users register, create a single personal bank account, deposit and withdraw money, and review a searchable, paginated transaction history with dashboard statistics. Every financial operation is performed inside a database transaction, all money fields use `Decimal`, and every query is scoped to the logged-in user so no one can ever view or modify another user's account.

## Features

- User registration, login, and logout using Django's built-in authentication system
- `@login_required` protection on every banking page
- One bank account per user (`OneToOneField`), account number uniqueness enforced
- Deposit money with validation (amount must be > 0)
- Withdraw money with overdraft prevention (never allows a negative balance)
- Full transaction history with type, amount, date/time, and balance-after-transaction
- Search and filter transactions by type and date range (GET query parameters)
- Dashboard with ORM-aggregated statistics: current balance, total deposits, total withdrawals, total transaction count
- Responsive Bootstrap 5 UI (desktop, tablet, mobile)
- Django messages framework for success/error feedback
- Django admin panel for `BankAccount` and `Transaction`

### Bonus features implemented

1. **Pagination** — 10 transactions per page, Bootstrap-styled page controls
2. **CSV Export** — download your own transaction history as CSV (`/transactions/export/`)
3. **Monthly Summary** — pick a month on the dashboard to see that month's deposits, withdrawals, and transaction count
4. **Charts** — Chart.js bar chart comparing deposits vs withdrawals over the last 6 months, built only from the logged-in user's data

## Technologies

- Python 3
- Django
- SQLite
- Bootstrap 5 (CDN)
- Bootstrap Icons (CDN)
- Chart.js (CDN)

## Installation

```bash
git clone <repository-url>
cd bank_transaction_system

python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt

python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

Then open http://127.0.0.1:8000/ in your browser.

A sample `db.sqlite3` with seeded data is already included in this repository for convenience, but running the commands above from a fresh clone also works — `seed_data` is safe to re-run (it skips users that already exist).

## Sample Login

These are **development-only** credentials for evaluation. Do NOT reuse them in production.

| Username     | Password       |
|--------------|----------------|
| mehedi       | test12345      |
| shakil       | test12345      |


Each sample user has a bank account pre-loaded with several deposit and withdrawal transactions.

A Django admin superuser is also available:

| Username | Password       | URL             |
|----------|----------------|-----------------|
| robin    |     robin      | `/admin/`       |

