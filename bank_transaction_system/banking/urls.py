from django.urls import path

from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('account/create/', views.create_account_view, name='account_create'),
    path('deposit/', views.deposit_view, name='deposit'),
    path('withdraw/', views.withdraw_view, name='withdraw'),
    path('transactions/', views.transaction_history_view, name='transaction_history'),
    path('transactions/export/', views.export_transactions_csv_view, name='transaction_export'),
]
