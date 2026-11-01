from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class StudyFlowAuthenticationTests(TestCase):
    def test_register_then_dashboard(self):
        response = self.client.post(reverse('register'), {
            'name': 'Ali',
            'email': 'ali@example.com',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
        })
        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue(get_user_model().objects.filter(email='ali@example.com').exists())
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'Ali')

    def test_wrong_login_does_not_authenticate(self):
        get_user_model().objects.create_user(
            username='ali@example.com', email='ali@example.com', password='RightPassword123!'
        )
        response = self.client.post(reverse('login'), {
            'email': 'ali@example.com', 'password': 'bad-password'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'noto‘g‘ri')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_and_post_only_logout(self):
        get_user_model().objects.create_user(
            username='test@example.com', email='test@example.com', password='Password123!'
        )
        self.assertRedirects(self.client.post(reverse('login'), {
            'email': 'test@example.com', 'password': 'Password123!'
        }), reverse('dashboard'))
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertRedirects(self.client.post(reverse('logout')), reverse('home'))
        self.assertRedirects(self.client.get(reverse('dashboard')), '/login/?next=/dashboard/')

    def test_register_rejects_mismatched_passwords(self):
        response = self.client.post(reverse('register'), {
            'name': 'Ali', 'email': 'ali@example.com',
            'password': 'StrongPassword123!', 'confirm_password': 'DifferentPassword123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Parollar mos emas')
        self.assertFalse(get_user_model().objects.filter(email='ali@example.com').exists())
