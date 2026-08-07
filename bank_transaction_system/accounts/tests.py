from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class RegistrationTests(TestCase):
    def test_registration_creates_user(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'new@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_registration_rejects_mismatched_passwords(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser2',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'new2@example.com',
            'password1': 'StrongPass123!',
            'password2': 'DifferentPass123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='newuser2').exists())

    def test_registration_rejects_duplicate_username(self):
        User.objects.create_user(username='existing', password='StrongPass123!')
        response = self.client.post(reverse('register'), {
            'username': 'existing',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'unique@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already exists')


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='loginuser', password='StrongPass123!')

    def test_login_success(self):
        response = self.client.post(reverse('login'), {
            'username': 'loginuser',
            'password': 'StrongPass123!',
        })
        self.assertEqual(response.status_code, 302)

    def test_login_failure_shows_error(self):
        response = self.client.post(reverse('login'), {
            'username': 'loginuser',
            'password': 'WrongPassword',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password')

    def test_logout(self):
        self.client.login(username='loginuser', password='StrongPass123!')
        response = self.client.post(reverse('logout'))
        self.assertEqual(response.status_code, 302)


class AuthenticationProtectionTests(TestCase):
    def test_unauthenticated_user_redirected_from_dashboard(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)
