from decimal import Decimal

from django import forms

from .models import BankAccount


class BootstrapFormMixin:
    """Adds Bootstrap's form-control class to every field's widget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (existing + ' form-control').strip()


class BankAccountForm(BootstrapFormMixin, forms.ModelForm):
    """
    Account creation form. current_balance is deliberately NOT part of this
    form - it is always set to 0.00 in the view so a user can never set
    their own starting balance.
    """

    class Meta:
        model = BankAccount
        fields = ['account_holder_name', 'account_number']

    def clean_account_number(self):
        account_number = self.cleaned_data['account_number'].strip()
        if not account_number:
            raise forms.ValidationError('Account number is required.')
        if BankAccount.objects.filter(account_number=account_number).exists():
            raise forms.ValidationError('This account number is already in use.')
        return account_number


class DepositForm(BootstrapFormMixin, forms.Form):
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
        error_messages={
            'min_value': 'Deposit amount must be greater than 0.',
            'required': 'Please enter an amount to deposit.',
        },
    )

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError('Deposit amount must be greater than 0.')
        return amount


class WithdrawForm(BootstrapFormMixin, forms.Form):
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
        error_messages={
            'min_value': 'Withdrawal amount must be greater than 0.',
            'required': 'Please enter an amount to withdraw.',
        },
    )

    def __init__(self, *args, current_balance=None, **kwargs):
        self.current_balance = current_balance
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError('Withdrawal amount must be greater than 0.')
        if self.current_balance is not None and amount > self.current_balance:
            raise forms.ValidationError('Insufficient balance.')
        return amount


class TransactionFilterForm(forms.Form):
    """Search/filter form used on the transaction history page (GET request)."""

    TYPE_CHOICES = [('', 'All')] + list(
        [('deposit', 'Deposit'), ('withdrawal', 'Withdrawal')]
    )

    type = forms.ChoiceField(choices=TYPE_CHOICES, required=False)
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing = field.widget.attrs.get('class', '')
            css_class = 'form-select' if isinstance(field, forms.ChoiceField) else 'form-control'
            field.widget.attrs['class'] = f'{existing} {css_class}'.strip()
