# users/tests.py

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User # If you need to create test users

class HomepageViewTest(TestCase):

    def setUp(self):
        # setUp runs before each test method in the class
        # We create a Client instance to simulate web requests
        self.client = Client()
        # Get the URL for the homepage using its name
        self.homepage_url = reverse('homepage')

    def test_homepage_loads_for_logged_out_user(self):
        """
        Test that the homepage returns a 200 status code
        and uses the correct template for anonymous users.
        """
        # Make a GET request to the homepage URL
        response = self.client.get(self.homepage_url)

        # Check 1: Was the response successful (status code 200)?
        self.assertEqual(response.status_code, 200)

        # Check 2: Did it use the correct template?
        self.assertTemplateUsed(response, 'users/homepage.html')

    def test_homepage_redirects_logged_in_user(self):
        """
        Test that the homepage redirects authenticated users
        to their dashboard.
        """
        # Create a dummy user for testing
        test_user = User.objects.create_user(username='testuser', password='password123')
        # Log the user in using the test client
        self.client.login(username='testuser', password='password123')

        # Make a GET request to the homepage URL *while logged in*
        response = self.client.get(self.homepage_url)

        # Check 1: Was the response a redirect (status code 302)?
        self.assertEqual(response.status_code, 302)

        # Check 2: Did it redirect to the dashboard URL?
        dashboard_url = reverse('users:dashboard')
        self.assertRedirects(response, dashboard_url)