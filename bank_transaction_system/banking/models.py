from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class BankAccount(models.Model):
    """
    One bank account per user. The account's current balance is the single
    source of truth for how much money the user has; it is only ever
    changed through the deposit/withdraw views inside a DB transaction.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bank_account',
    )
    account_holder_name = models.CharField(max_length=150)
    account_number = models.CharField(max_length=20, unique=True)
    current_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.account_holder_name} ({self.account_number})'


class Transaction(models.Model):
    """
    A single deposit or withdrawal against a BankAccount. balance_after
    stores a snapshot of the account balance immediately after this
    transaction so the transaction history never needs to be recalculated.
    """

    DEPOSIT = 'deposit'
    WITHDRAWAL = 'withdrawal'
    TRANSACTION_TYPES = [
        (DEPOSIT, 'Deposit'),
        (WITHDRAWAL, 'Withdrawal'),
    ]

    account = models.ForeignKey(
        BankAccount,
        on_delete=models.CASCADE,
        related_name='transactions',
    )
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    balance_after_transaction = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_transaction_type_display()} of {self.amount} on {self.account.account_number}'
