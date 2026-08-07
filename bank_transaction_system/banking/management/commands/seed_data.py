from decimal import Decimal
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction as db_transaction
from django.utils import timezone

from banking.models import BankAccount, Transaction

# Development-only sample credentials. DO NOT use these in production.
SAMPLE_USERS = [
    {
        'username': 'john_doe',
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john.doe@example.com',
        'password': 'Sample@1234',
        'account_number': '1000000001',
    },
    {
        'username': 'jane_smith',
        'first_name': 'Jane',
        'last_name': 'Smith',
        'email': 'jane.smith@example.com',
        'password': 'Sample@1234',
        'account_number': '1000000002',
    },
    {
        'username': 'rahim_uddin',
        'first_name': 'Rahim',
        'last_name': 'Uddin',
        'email': 'rahim.uddin@example.com',
        'password': 'Sample@1234',
        'account_number': '1000000003',
    },
]


class Command(BaseCommand):
    help = 'Seeds the database with sample users, bank accounts, and transactions for evaluation.'

    def handle(self, *args, **options):
        with db_transaction.atomic():
            for entry in SAMPLE_USERS:
                self._seed_user(entry)

        self.stdout.write(self.style.SUCCESS('Sample data created successfully.'))
        self.stdout.write(self.style.WARNING(
            'These are development-only credentials. Do NOT use them in production.'
        ))
        for entry in SAMPLE_USERS:
            self.stdout.write(f"  username: {entry['username']}  password: {entry['password']}")

    def _seed_user(self, entry):
        user, created = User.objects.get_or_create(
            username=entry['username'],
            defaults={
                'first_name': entry['first_name'],
                'last_name': entry['last_name'],
                'email': entry['email'],
            },
        )
        if created:
            user.set_password(entry['password'])
            user.save()
            self.stdout.write(f"Created user: {entry['username']}")
        else:
            self.stdout.write(f"User already exists, skipping: {entry['username']}")
            return

        account, _ = BankAccount.objects.get_or_create(
            user=user,
            defaults={
                'account_holder_name': f"{entry['first_name']} {entry['last_name']}",
                'account_number': entry['account_number'],
                'current_balance': Decimal('0.00'),
            },
        )

        # A handful of deposit and withdrawal transactions with a running balance.
        now = timezone.now()
        movements = [
            (Transaction.DEPOSIT, Decimal('20000.00'), 10),
            (Transaction.DEPOSIT, Decimal('5000.00'), 8),
            (Transaction.WITHDRAWAL, Decimal('3000.00'), 6),
            (Transaction.DEPOSIT, Decimal('7500.00'), 4),
            (Transaction.WITHDRAWAL, Decimal('2000.00'), 2),
            (Transaction.DEPOSIT, Decimal('1200.00'), 1),
        ]

        balance = account.current_balance
        for transaction_type, amount, days_ago in movements:
            if transaction_type == Transaction.DEPOSIT:
                balance += amount
            else:
                balance -= amount
            txn = Transaction.objects.create(
                account=account,
                transaction_type=transaction_type,
                amount=amount,
                balance_after_transaction=balance,
            )
            # Backdate created_at for a realistic-looking history.
            Transaction.objects.filter(pk=txn.pk).update(
                created_at=now - timedelta(days=days_ago)
            )

        account.current_balance = balance
        account.save()
        self.stdout.write(f"Seeded account {account.account_number} with balance {balance}")
