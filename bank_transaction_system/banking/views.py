import csv
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction as db_transaction
from django.db.models import Sum, Count, Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import BankAccountForm, DepositForm, WithdrawForm, TransactionFilterForm
from .models import BankAccount, Transaction


def get_user_account(request):
    """
    Single, safe way to fetch the logged-in user's bank account.
    Always derives the account from request.user - never from a URL or
    query parameter - so a user can never reach another user's account.
    """
    return BankAccount.objects.filter(user=request.user).first()


@login_required
def create_account_view(request):
    """Let a logged-in user create their one-and-only bank account."""
    existing_account = get_user_account(request)
    if existing_account:
        messages.info(request, 'You already have a bank account.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = BankAccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.user = request.user
            account.current_balance = Decimal('0.00')  # never user-supplied
            account.save()
            messages.success(request, 'Bank account created successfully.')
            return redirect('dashboard')
        messages.error(request, 'Please fix the errors below and try again.')
    else:
        form = BankAccountForm(initial={
            'account_holder_name': request.user.get_full_name() or request.user.username
        })

    return render(request, 'banking/account_form.html', {'form': form})


@login_required
def dashboard_view(request):
    account = get_user_account(request)
    if not account:
        messages.info(request, 'Please create a bank account to get started.')
        return redirect('account_create')

    # Aggregation done via the ORM, not manually in the template.
    totals = account.transactions.aggregate(
        total_deposits=Sum('amount', filter=Q(transaction_type=Transaction.DEPOSIT)),
        total_withdrawals=Sum('amount', filter=Q(transaction_type=Transaction.WITHDRAWAL)),
        total_transactions=Count('id'),
    )
    total_deposits = totals['total_deposits'] or Decimal('0.00')
    total_withdrawals = totals['total_withdrawals'] or Decimal('0.00')
    total_transactions = totals['total_transactions'] or 0

    recent_transactions = account.transactions.all()[:5]

    # Bonus: monthly summary for the currently selected month (defaults to this month)
    today = timezone.localdate()
    month_str = request.GET.get('month')  # format YYYY-MM
    if month_str:
        try:
            year, month = (int(part) for part in month_str.split('-'))
        except (ValueError, TypeError):
            year, month = today.year, today.month
    else:
        year, month = today.year, today.month

    monthly_qs = account.transactions.filter(created_at__year=year, created_at__month=month)
    monthly_totals = monthly_qs.aggregate(
        monthly_deposits=Sum('amount', filter=Q(transaction_type=Transaction.DEPOSIT)),
        monthly_withdrawals=Sum('amount', filter=Q(transaction_type=Transaction.WITHDRAWAL)),
        monthly_count=Count('id'),
    )

    # Bonus: chart data - deposits vs withdrawals for the last 6 months (including current)
    chart_labels = []
    chart_deposits = []
    chart_withdrawals = []
    months_data = []
    y, m = today.year, today.month
    for _ in range(6):
        totals_m = account.transactions.filter(created_at__year=y, created_at__month=m).aggregate(
            d=Sum('amount', filter=Q(transaction_type=Transaction.DEPOSIT)),
            w=Sum('amount', filter=Q(transaction_type=Transaction.WITHDRAWAL)),
        )
        months_data.append((y, m, totals_m['d'] or Decimal('0.00'), totals_m['w'] or Decimal('0.00')))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    months_data.reverse()
    for y, m, d, w in months_data:
        chart_labels.append(f'{y}-{m:02d}')
        chart_deposits.append(float(d))
        chart_withdrawals.append(float(w))

    context = {
        'account': account,
        'total_deposits': total_deposits,
        'total_withdrawals': total_withdrawals,
        'total_transactions': total_transactions,
        'recent_transactions': recent_transactions,
        'selected_month': f'{year:04d}-{month:02d}',
        'monthly_deposits': monthly_totals['monthly_deposits'] or Decimal('0.00'),
        'monthly_withdrawals': monthly_totals['monthly_withdrawals'] or Decimal('0.00'),
        'monthly_count': monthly_totals['monthly_count'] or 0,
        'chart_labels': chart_labels,
        'chart_deposits': chart_deposits,
        'chart_withdrawals': chart_withdrawals,
    }
    return render(request, 'banking/dashboard.html', context)


@login_required
def deposit_view(request):
    account = get_user_account(request)
    if not account:
        messages.info(request, 'Please create a bank account first.')
        return redirect('account_create')

    if request.method == 'POST':
        form = DepositForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            with db_transaction.atomic():
                # Lock the row for the duration of this transaction to avoid races.
                locked_account = BankAccount.objects.select_for_update().get(pk=account.pk)
                locked_account.current_balance = locked_account.current_balance + amount
                locked_account.save()
                Transaction.objects.create(
                    account=locked_account,
                    transaction_type=Transaction.DEPOSIT,
                    amount=amount,
                    balance_after_transaction=locked_account.current_balance,
                )
            messages.success(request, 'Money deposited successfully.')
            return redirect('dashboard')
        messages.error(request, 'Please correct the error below.')
    else:
        form = DepositForm()

    return render(request, 'banking/deposit.html', {'form': form, 'account': account})


@login_required
def withdraw_view(request):
    account = get_user_account(request)
    if not account:
        messages.info(request, 'Please create a bank account first.')
        return redirect('account_create')

    if request.method == 'POST':
        form = WithdrawForm(request.POST, current_balance=account.current_balance)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            with db_transaction.atomic():
                locked_account = BankAccount.objects.select_for_update().get(pk=account.pk)
                if amount > locked_account.current_balance:
                    messages.error(request, 'Insufficient balance.')
                    return render(request, 'banking/withdraw.html', {'form': form, 'account': account})
                locked_account.current_balance = locked_account.current_balance - amount
                locked_account.save()
                Transaction.objects.create(
                    account=locked_account,
                    transaction_type=Transaction.WITHDRAWAL,
                    amount=amount,
                    balance_after_transaction=locked_account.current_balance,
                )
            messages.success(request, 'Money withdrawn successfully.')
            return redirect('dashboard')
        messages.error(request, 'Please correct the error below.')
    else:
        form = WithdrawForm(current_balance=account.current_balance)

    return render(request, 'banking/withdraw.html', {'form': form, 'account': account})


def _filtered_transactions(request, account):
    """Shared filtering logic for the history page and the CSV export."""
    filter_form = TransactionFilterForm(request.GET or None)
    qs = account.transactions.all()

    if filter_form.is_valid():
        transaction_type = filter_form.cleaned_data.get('type')
        start_date = filter_form.cleaned_data.get('start_date')
        end_date = filter_form.cleaned_data.get('end_date')

        if transaction_type:
            qs = qs.filter(transaction_type=transaction_type)
        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)

    return qs, filter_form


@login_required
def transaction_history_view(request):
    account = get_user_account(request)
    if not account:
        messages.info(request, 'Please create a bank account first.')
        return redirect('account_create')

    transactions, filter_form = _filtered_transactions(request, account)

    # Bonus: pagination - 10 transactions per page.
    paginator = Paginator(transactions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Preserve filters when building pagination/export links, without a stale "page" param.
    querystring = request.GET.copy()
    querystring.pop('page', None)

    context = {
        'account': account,
        'page_obj': page_obj,
        'filter_form': filter_form,
        'querystring': querystring.urlencode(),
    }
    return render(request, 'banking/transactions.html', context)


@login_required
def export_transactions_csv_view(request):
    """Bonus: export ONLY the logged-in user's transactions as CSV."""
    account = get_user_account(request)
    if not account:
        messages.info(request, 'Please create a bank account first.')
        return redirect('account_create')

    transactions, _ = _filtered_transactions(request, account)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="transactions.csv"'

    writer = csv.writer(response)
    writer.writerow(['Transaction Type', 'Amount', 'Date & Time', 'Balance After Transaction'])
    for txn in transactions:
        writer.writerow([
            txn.get_transaction_type_display(),
            txn.amount,
            txn.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            txn.balance_after_transaction,
        ])

    return response
