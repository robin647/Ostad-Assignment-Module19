from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import BankAccount, Transaction


class BankAccountCreationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='StrongPass123!')
        self.client.login(username='alice', password='StrongPass123!')

    def test_user_can_create_account(self):
        response = self.client.post(reverse('account_create'), {
            'account_holder_name': 'Alice Doe',
            'account_number': '5000000001',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(BankAccount.objects.filter(user=self.user).exists())
        account = BankAccount.objects.get(user=self.user)
        self.assertEqual(account.current_balance, Decimal('0.00'))

    def test_user_cannot_create_duplicate_account(self):
        BankAccount.objects.create(
            user=self.user, account_holder_name='Alice Doe', account_number='5000000002'
        )
        response = self.client.post(reverse('account_create'), {
            'account_holder_name': 'Alice Doe',
            'account_number': '5000000003',
        })
        # Should be redirected away without creating a second account.
        self.assertEqual(response.status_code, 302)
        self.assertEqual(BankAccount.objects.filter(user=self.user).count(), 1)


class DepositTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='bob', password='StrongPass123!')
        self.account = BankAccount.objects.create(
            user=self.user, account_holder_name='Bob Doe', account_number='5000000010',
            current_balance=Decimal('10000.00'),
        )
        self.client.login(username='bob', password='StrongPass123!')

    def test_positive_deposit_updates_balance_and_creates_transaction(self):
        response = self.client.post(reverse('deposit'), {'amount': '2000'})
        self.assertEqual(response.status_code, 302)
        self.account.refresh_from_db()
        self.assertEqual(self.account.current_balance, Decimal('12000.00'))
        txn = Transaction.objects.get(account=self.account)
        self.assertEqual(txn.transaction_type, Transaction.DEPOSIT)
        self.assertEqual(txn.amount, Decimal('2000.00'))
        self.assertEqual(txn.balance_after_transaction, Decimal('12000.00'))

    def test_zero_deposit_rejected(self):
        response = self.client.post(reverse('deposit'), {'amount': '0'})
        self.assertEqual(response.status_code, 200)
        self.account.refresh_from_db()
        self.assertEqual(self.account.current_balance, Decimal('10000.00'))
        self.assertEqual(Transaction.objects.filter(account=self.account).count(), 0)

    def test_negative_deposit_rejected(self):
        response = self.client.post(reverse('deposit'), {'amount': '-500'})
        self.assertEqual(response.status_code, 200)
        self.account.refresh_from_db()
        self.assertEqual(self.account.current_balance, Decimal('10000.00'))


class WithdrawalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='carol', password='StrongPass123!')
        self.account = BankAccount.objects.create(
            user=self.user, account_holder_name='Carol Doe', account_number='5000000020',
            current_balance=Decimal('10000.00'),
        )
        self.client.login(username='carol', password='StrongPass123!')

    def test_positive_withdrawal_updates_balance_and_creates_transaction(self):
        response = self.client.post(reverse('withdraw'), {'amount': '3000'})
        self.assertEqual(response.status_code, 302)
        self.account.refresh_from_db()
        self.assertEqual(self.account.current_balance, Decimal('7000.00'))
        txn = Transaction.objects.get(account=self.account)
        self.assertEqual(txn.transaction_type, Transaction.WITHDRAWAL)
        self.assertEqual(txn.balance_after_transaction, Decimal('7000.00'))

    def test_zero_withdrawal_rejected(self):
        response = self.client.post(reverse('withdraw'), {'amount': '0'})
        self.assertEqual(response.status_code, 200)
        self.account.refresh_from_db()
        self.assertEqual(self.account.current_balance, Decimal('10000.00'))

    def test_negative_withdrawal_rejected(self):
        response = self.client.post(reverse('withdraw'), {'amount': '-100'})
        self.assertEqual(response.status_code, 200)
        self.account.refresh_from_db()
        self.assertEqual(self.account.current_balance, Decimal('10000.00'))

    def test_withdrawal_exceeding_balance_rejected(self):
        response = self.client.post(reverse('withdraw'), {'amount': '15000'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Insufficient balance')
        self.account.refresh_from_db()
        self.assertEqual(self.account.current_balance, Decimal('10000.00'))
        self.assertEqual(Transaction.objects.filter(account=self.account).count(), 0)

    def test_balance_never_goes_negative(self):
        self.client.post(reverse('withdraw'), {'amount': '10000'})
        self.account.refresh_from_db()
        self.assertEqual(self.account.current_balance, Decimal('0.00'))
        response = self.client.post(reverse('withdraw'), {'amount': '0.01'})
        self.assertContains(response, 'Insufficient balance')


class TransactionIsolationTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='dave', password='StrongPass123!')
        self.user2 = User.objects.create_user(username='erin', password='StrongPass123!')
        self.account1 = BankAccount.objects.create(
            user=self.user1, account_holder_name='Dave Doe', account_number='5000000030',
            current_balance=Decimal('5000.00'),
        )
        self.account2 = BankAccount.objects.create(
            user=self.user2, account_holder_name='Erin Doe', account_number='5000000031',
            current_balance=Decimal('9000.00'),
        )
        Transaction.objects.create(
            account=self.account1, transaction_type=Transaction.DEPOSIT,
            amount=Decimal('5000.00'), balance_after_transaction=Decimal('5000.00'),
        )

    def test_user_cannot_see_another_users_transactions(self):
        self.client.login(username='erin', password='StrongPass123!')
        response = self.client.get(reverse('transaction_history'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.account1.account_number)

    def test_dashboard_only_shows_own_account(self):
        self.client.login(username='dave', password='StrongPass123!')
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, self.account1.account_number)
        self.assertNotContains(response, self.account2.account_number)


class DashboardTemplateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='grace', password='StrongPass123!')
        self.account = BankAccount.objects.create(
            user=self.user, account_holder_name='Grace Doe', account_number='5000000050',
            current_balance=Decimal('0.00'),
        )
        self.client.login(username='grace', password='StrongPass123!')

    def test_dashboard_renders_chart_data_and_branding(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="chart-labels"')
        self.assertContains(response, 'id="chart-deposits"')
        self.assertContains(response, 'id="chart-withdrawals"')
        self.assertContains(response, 'MHR Bank')


class DashboardAggregationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='frank', password='StrongPass123!')
        self.account = BankAccount.objects.create(
            user=self.user, account_holder_name='Frank Doe', account_number='5000000040',
            current_balance=Decimal('0.00'),
        )
        self.client.login(username='frank', password='StrongPass123!')
        self.client.post(reverse('deposit'), {'amount': '5000'})
        self.client.post(reverse('deposit'), {'amount': '2000'})
        self.client.post(reverse('withdraw'), {'amount': '1000'})

    def test_dashboard_totals_are_correct(self):
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, '6000.00')  # current balance
        self.assertContains(response, '7000.00')  # total deposits
        self.assertContains(response, '1000.00')  # total withdrawals
        self.account.refresh_from_db()
        self.assertEqual(self.account.current_balance, Decimal('6000.00'))
        self.assertEqual(Transaction.objects.filter(account=self.account).count(), 3)
