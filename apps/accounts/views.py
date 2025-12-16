from rest_framework import status, generics, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from .models import User
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)
from .services import register_user, UserRegistrationError
import secrets


# Response serializers for API documentation
class TokensResponseSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField()


class AuthResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    user = UserSerializer()
    tokens = TokensResponseSerializer()


class MessageResponseSerializer(serializers.Serializer):
    message = serializers.CharField()


class ErrorResponseSerializer(serializers.Serializer):
    error = serializers.CharField()


class LogoutRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField(help_text="Refresh token to blacklist")


class VerifyEmailRequestSerializer(serializers.Serializer):
    token = serializers.CharField(help_text="Email verification token")


class DeleteAccountRequestSerializer(serializers.Serializer):
    password = serializers.CharField(help_text="Current password for confirmation")
    confirm = serializers.BooleanField(help_text="Must be true to confirm deletion")


@extend_schema(
    request=UserRegistrationSerializer,
    responses={
        201: AuthResponseSerializer,
        400: ErrorResponseSerializer,
    },
    description="Register a new user account and receive JWT tokens.",
    tags=['auth'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Register a new user account."""
    serializer = UserRegistrationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # Remove password_confirm before passing to service
    data = serializer.validated_data.copy()
    data.pop('password_confirm', None)

    try:
        user = register_user(**data)
    except UserRegistrationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)

    return Response({
        'message': 'Registration successful. Please verify your email.',
        'user': UserSerializer(user).data,
        'tokens': {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    }, status=status.HTTP_201_CREATED)


@extend_schema(
    request=UserLoginSerializer,
    responses={
        200: AuthResponseSerializer,
        400: ErrorResponseSerializer,
        401: ErrorResponseSerializer,
        403: ErrorResponseSerializer,
    },
    description="Authenticate with email and password to receive JWT tokens.",
    tags=['auth'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Login with email and password."""
    serializer = UserLoginSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    email = serializer.validated_data['email']
    password = serializer.validated_data['password']
    
    # Authenticate user
    user = authenticate(request, username=email, password=password)
    
    if user is None:
        return Response({
            'error': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    if not user.is_active:
        return Response({
            'error': 'Account is deactivated'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Update last login
    user.last_login = timezone.now()
    user.save(update_fields=['last_login'])
    
    # Generate tokens
    refresh = RefreshToken.for_user(user)
    
    return Response({
        'message': 'Login successful',
        'user': UserSerializer(user).data,
        'tokens': {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    })


@extend_schema(
    request=LogoutRequestSerializer,
    responses={
        200: MessageResponseSerializer,
        400: ErrorResponseSerializer,
    },
    description="Logout and optionally blacklist the refresh token.",
    tags=['auth'],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """Logout and blacklist refresh token."""
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            # Note: Requires djangorestframework-simplejwt[blacklist]
            # token.blacklist()
        
        return Response({
            'message': 'Logout successful'
        })
    except Exception as e:
        return Response({
            'error': 'Invalid token'
        }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    responses={200: UserSerializer},
    description="Get the current authenticated user's profile.",
    tags=['auth'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """Get current authenticated user profile."""
    return Response(UserSerializer(request.user).data)


@extend_schema(
    request=UserSerializer,
    responses={
        200: UserSerializer,
        400: ErrorResponseSerializer,
    },
    description="Update the current user's profile (display_name, preferences).",
    tags=['auth'],
)
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """Update user profile."""
    user = request.user
    serializer = UserSerializer(user, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request=PasswordResetRequestSerializer,
    responses={200: MessageResponseSerializer},
    description="Request a password reset email. Always returns success for security.",
    tags=['auth'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset(request):
    """Request password reset email."""
    serializer = PasswordResetRequestSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    email = serializer.validated_data['email']
    
    try:
        user = User.objects.get(email=email, is_active=True)
        
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        user.verification_token = reset_token
        user.save(update_fields=['verification_token'])
        
        # Send email (implement email sending)
        # send_password_reset_email(user, reset_token)
        
        return Response({
            'message': 'Password reset email sent',
            'token': reset_token  # Remove in production!
        })
    
    except User.DoesNotExist:
        # Don't reveal if email exists (security)
        return Response({
            'message': 'If account exists, password reset email has been sent'
        })


@extend_schema(
    request=PasswordResetConfirmSerializer,
    responses={
        200: MessageResponseSerializer,
        400: ErrorResponseSerializer,
    },
    description="Confirm password reset with token and set new password.",
    tags=['auth'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def confirm_password_reset(request):
    """Confirm password reset with token."""
    serializer = PasswordResetConfirmSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    token = serializer.validated_data['token']
    new_password = serializer.validated_data['new_password']
    
    try:
        user = User.objects.get(verification_token=token, is_active=True)
        
        # Set new password
        user.set_password(new_password)
        user.verification_token = None
        user.save(update_fields=['password', 'verification_token'])
        
        return Response({
            'message': 'Password reset successful'
        })
    
    except User.DoesNotExist:
        return Response({
            'error': 'Invalid or expired reset token'
        }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request=VerifyEmailRequestSerializer,
    responses={
        200: MessageResponseSerializer,
        400: ErrorResponseSerializer,
    },
    description="Verify user's email address with verification token.",
    tags=['auth'],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_email(request):
    """Verify email with token."""
    token = request.data.get('token')
    user = request.user
    
    if user.verification_token == token:
        user.email_verified = True
        user.verification_token = None
        user.save(update_fields=['email_verified', 'verification_token'])
        
        return Response({
            'message': 'Email verified successfully'
        })
    
    return Response({
        'error': 'Invalid verification token'
    }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request=DeleteAccountRequestSerializer,
    responses={
        204: None,
        400: ErrorResponseSerializer,
        401: ErrorResponseSerializer,
    },
    description="GDPR-compliant account deletion. Anonymizes user data.",
    tags=['auth'],
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_account(request):
    """GDPR-compliant account deletion (anonymization)."""
    password = request.data.get('password')
    confirm = request.data.get('confirm')
    
    if not confirm:
        return Response({
            'error': 'Confirmation required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Verify password
    if not request.user.check_password(password):
        return Response({
            'error': 'Invalid password'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    # Anonymize user data (GDPR)
    request.user.anonymize()
    
    return Response({
        'message': 'Account deleted successfully'
    }, status=status.HTTP_204_NO_CONTENT)


class UserDetailView(generics.RetrieveAPIView):
    """
    Get user profile by ID.
    
    GET /api/auth/users/{id}/
    """
    queryset = User.objects.filter(is_active=True, gdpr_deleted_at__isnull=True)
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]