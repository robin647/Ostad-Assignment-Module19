from django.urls import path

from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.BankLoginView.as_view(), name='login'),
    path('logout/', views.BankLogoutView.as_view(), name='logout'),
]
