import pytest
from django.urls import reverse
from rest_framework import status
from apps.accounts.models import User


# =============================================================================
# Registration Tests
# =============================================================================

@pytest.mark.django_db
class TestRegistration:
    """Tests for POST /api/auth/register/"""

    def test_register_success(self, api_client):
        """Successfully register a new user."""
        url = reverse('users:register')
        data = {
            'email': 'newuser@example.com',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
            'display_name': 'New User',
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert 'tokens' in response.data
        assert 'access' in response.data['tokens']
        assert 'refresh' in response.data['tokens']
        assert User.objects.filter(email='newuser@example.com').exists()

    def test_register_without_display_name(self, api_client):
        """Register without display name (optional field)."""
        url = reverse('users:register')
        data = {
            'email': 'minimal@example.com',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(email='minimal@example.com').exists()

    def test_register_duplicate_email(self, api_client, user):
        """Cannot register with existing email."""
        url = reverse('users:register')
        data = {
            'email': user.email,
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_password_mismatch(self, api_client):
        """Registration fails when passwords don't match."""
        url = reverse('users:register')
        data = {
            'email': 'mismatch@example.com',
            'password': 'SecurePass123!',
            'password_confirm': 'DifferentPass123!',
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password_confirm' in response.data

    def test_register_weak_password(self, api_client):
        """Registration fails with weak password."""
        url = reverse('users:register')
        data = {
            'email': 'weak@example.com',
            'password': '123',
            'password_confirm': '123',
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_invalid_email(self, api_client):
        """Registration fails with invalid email format."""
        url = reverse('users:register')
        data = {
            'email': 'not-an-email',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Login Tests
# =============================================================================

@pytest.mark.django_db
class TestLogin:
    """Tests for POST /api/auth/login/"""

    def test_login_success(self, api_client, user):
        """Successfully login with valid credentials."""
        url = reverse('users:login')
        data = {
            'email': user.email,
            'password': 'TestPass123!',
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert 'tokens' in response.data
        assert 'access' in response.data['tokens']
        assert 'refresh' in response.data['tokens']
        assert response.data['user']['email'] == user.email

    def test_login_wrong_password(self, api_client, user):
        """Login fails with wrong password."""
        url = reverse('users:login')
        data = {
            'email': user.email,
            'password': 'WrongPassword123!',
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'error' in response.data

    def test_login_nonexistent_user(self, api_client):
        """Login fails for non-existent user."""
        url = reverse('users:login')
        data = {
            'email': 'nonexistent@example.com',
            'password': 'SomePass123!',
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_inactive_user(self, api_client, user_inactive):
        """Login fails for inactive user."""
        url = reverse('users:login')
        data = {
            'email': user_inactive.email,
            'password': 'TestPass123!',
        }
        response = api_client.post(url, data)

        # Inactive users should not be able to login
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        )

    def test_login_updates_last_login(self, api_client, user):
        """Login updates last_login timestamp."""
        original_last_login = user.last_login
        url = reverse('users:login')
        data = {
            'email': user.email,
            'password': 'TestPass123!',
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.last_login != original_last_login
        assert user.last_login is not None


# =============================================================================
# Logout Tests
# =============================================================================

@pytest.mark.django_db
class TestLogout:
    """Tests for POST /api/auth/logout/"""

    def test_logout_success(self, authenticated_client):
        """Successfully logout."""
        url = reverse('users:logout')
        # Logout without providing refresh token (optional in current impl)
        response = authenticated_client.post(url, {})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['message'] == 'Logout successful'

    def test_logout_unauthenticated(self, api_client):
        """Logout requires authentication."""
        url = reverse('users:logout')
        response = api_client.post(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Get Current User Tests
# =============================================================================

@pytest.mark.django_db
class TestGetCurrentUser:
    """Tests for GET /api/auth/user/"""

    def test_get_current_user(self, authenticated_client, user):
        """Get current authenticated user profile."""
        url = reverse('users:current-user')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == user.email
        assert response.data['display_name'] == user.display_name
        assert 'id' in response.data

    def test_get_current_user_unauthenticated(self, api_client):
        """Cannot get user profile when not authenticated."""
        url = reverse('users:current-user')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Update Profile Tests
# =============================================================================

@pytest.mark.django_db
class TestUpdateProfile:
    """Tests for PATCH /api/auth/user/update/"""

    def test_update_display_name(self, authenticated_client, user):
        """Update user display name."""
        url = reverse('users:update-profile')
        data = {'display_name': 'Updated Name'}
        response = authenticated_client.patch(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['display_name'] == 'Updated Name'
        user.refresh_from_db()
        assert user.display_name == 'Updated Name'

    def test_update_preferences(self, authenticated_client, user):
        """Update user preferences."""
        url = reverse('users:update-profile')
        data = {'preferences': {'theme': 'dark', 'notifications': True}}
        response = authenticated_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.preferences['theme'] == 'dark'

    def test_update_profile_unauthenticated(self, api_client):
        """Cannot update profile when not authenticated."""
        url = reverse('users:update-profile')
        data = {'display_name': 'Hacked'}
        response = api_client.patch(url, data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_cannot_update_email(self, authenticated_client, user):
        """Email is read-only and cannot be updated."""
        url = reverse('users:update-profile')
        original_email = user.email
        data = {'email': 'newemail@example.com'}
        response = authenticated_client.patch(url, data)

        # Either success with email unchanged, or validation error
        user.refresh_from_db()
        assert user.email == original_email


# =============================================================================
# Delete Account Tests
# =============================================================================

@pytest.mark.django_db
class TestDeleteAccount:
    """Tests for DELETE /api/auth/user/delete/"""

    def test_delete_account_success(self, authenticated_client, user):
        """Successfully delete account with GDPR anonymization."""
        url = reverse('users:delete-account')
        data = {
            'password': 'TestPass123!',
            'confirm': True,
        }
        response = authenticated_client.delete(url, data, format='json')

        assert response.status_code == status.HTTP_204_NO_CONTENT

        user.refresh_from_db()
        assert user.is_active is False
        assert user.gdpr_deleted_at is not None
        assert 'anonymized' in user.email

    def test_delete_account_wrong_password(self, authenticated_client, user):
        """Cannot delete account with wrong password."""
        url = reverse('users:delete-account')
        data = {
            'password': 'WrongPassword!',
            'confirm': True,
        }
        response = authenticated_client.delete(url, data, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        user.refresh_from_db()
        assert user.is_active is True

    def test_delete_account_without_confirmation(self, authenticated_client, user):
        """Cannot delete account without confirmation."""
        url = reverse('users:delete-account')
        data = {
            'password': 'TestPass123!',
            'confirm': False,
        }
        response = authenticated_client.delete(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        user.refresh_from_db()
        assert user.is_active is True

    def test_delete_account_unauthenticated(self, api_client):
        """Cannot delete account when not authenticated."""
        url = reverse('users:delete-account')
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Get User By ID Tests
# =============================================================================

@pytest.mark.django_db
class TestGetUserById:
    """Tests for GET /api/auth/users/{id}/"""

    def test_get_user_by_id(self, authenticated_client, other_user):
        """Get another user's profile by ID."""
        url = reverse('users:user-detail', args=[other_user.id])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == other_user.email

    def test_get_user_by_id_not_found(self, authenticated_client):
        """Return 404 for non-existent user ID."""
        import uuid
        url = reverse('users:user-detail', args=[uuid.uuid4()])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_user_by_id_unauthenticated(self, api_client, user):
        """Cannot get user by ID when not authenticated."""
        url = reverse('users:user-detail', args=[user.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Email Verification Tests
# =============================================================================

@pytest.mark.django_db
class TestEmailVerification:
    """Tests for POST /api/auth/verify-email/"""

    def test_verify_email_success(self, api_client, user_unverified):
        """Successfully verify email with valid token."""
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user_unverified)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        url = reverse('users:verify-email')
        data = {'token': 'test-verification-token'}
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        user_unverified.refresh_from_db()
        assert user_unverified.email_verified is True
        assert user_unverified.verification_token is None

    def test_verify_email_invalid_token(self, authenticated_client, user):
        """Verification fails with invalid token."""
        url = reverse('users:verify-email')
        data = {'token': 'invalid-token'}
        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_verify_email_unauthenticated(self, api_client):
        """Email verification requires authentication."""
        url = reverse('users:verify-email')
        data = {'token': 'some-token'}
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Password Reset Tests
# =============================================================================

@pytest.mark.django_db
class TestPasswordReset:
    """Tests for password reset flow."""

    def test_request_password_reset(self, api_client, user):
        """Request password reset for existing user."""
        url = reverse('users:password-reset')
        data = {'email': user.email}
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.verification_token is not None

    def test_request_password_reset_nonexistent_email(self, api_client):
        """Request password reset for non-existent email (no error revealed)."""
        url = reverse('users:password-reset')
        data = {'email': 'nonexistent@example.com'}
        response = api_client.post(url, data)

        # Should not reveal if email exists (security)
        assert response.status_code == status.HTTP_200_OK

    def test_confirm_password_reset_success(self, api_client, user_with_reset_token):
        """Successfully reset password with valid token."""
        url = reverse('users:password-reset-confirm')
        data = {
            'token': 'valid-reset-token-12345',
            'new_password': 'NewSecurePass123!',
            'new_password_confirm': 'NewSecurePass123!',
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK

        # Verify can login with new password
        user_with_reset_token.refresh_from_db()
        assert user_with_reset_token.check_password('NewSecurePass123!')
        assert user_with_reset_token.verification_token is None

    def test_confirm_password_reset_invalid_token(self, api_client):
        """Password reset fails with invalid token."""
        url = reverse('users:password-reset-confirm')
        data = {
            'token': 'invalid-token',
            'new_password': 'NewSecurePass123!',
            'new_password_confirm': 'NewSecurePass123!',
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_confirm_password_reset_password_mismatch(self, api_client, user_with_reset_token):
        """Password reset fails when passwords don't match."""
        url = reverse('users:password-reset-confirm')
        data = {
            'token': 'valid-reset-token-12345',
            'new_password': 'NewSecurePass123!',
            'new_password_confirm': 'DifferentPass123!',
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# User Model Tests
# =============================================================================

@pytest.mark.django_db
class TestUserModel:
    """Tests for User model methods."""

    def test_create_user(self, db):
        """Create user with create_user method."""
        user = User.objects.create_user(
            email='model@example.com',
            password='TestPass123!',
        )

        assert user.email == 'model@example.com'
        assert user.check_password('TestPass123!')
        assert user.is_active is True
        assert user.is_staff is False

    def test_create_superuser(self, db):
        """Create superuser with create_superuser method."""
        user = User.objects.create_superuser(
            email='admin@example.com',
            password='AdminPass123!',
        )

        assert user.is_staff is True
        assert user.is_superuser is True
        assert user.email_verified is True

    def test_get_display_name(self, user):
        """get_display_name returns display_name or email prefix."""
        assert user.get_display_name() == 'Test User'

        user.display_name = ''
        user.save()
        assert user.get_display_name() == 'testuser'

    def test_anonymize(self, user):
        """Anonymize user data for GDPR compliance."""
        original_id = user.id
        user.anonymize()

        assert user.is_active is False
        assert 'anonymized' in user.email
        assert user.display_name == 'Deleted User'
        assert user.gdpr_deleted_at is not None
        assert user.id == original_id  # ID preserved

    def test_user_str(self, user):
        """User string representation is email."""
        assert str(user) == user.email
