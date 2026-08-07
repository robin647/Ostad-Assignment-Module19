from django.contrib import admin

from .models import BankAccount, Transaction


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('account_number', 'account_holder_name', 'user', 'current_balance', 'created_at')
    search_fields = ('account_number', 'account_holder_name', 'user__username', 'user__email')
    list_filter = ('created_at',)
    ordering = ('-created_at',)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('account', 'transaction_type', 'amount', 'balance_after_transaction', 'created_at')
    search_fields = ('account__account_number', 'account__account_holder_name')
    list_filter = ('transaction_type', 'created_at')
    ordering = ('-created_at',)
