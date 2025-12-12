from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
from .models import User
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)
import secrets


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Register a new user account.
    
    POST /api/auth/register/
    Body: {
        "email": "user@example.com",
        "password": "securepassword",
        "display_name": "John Doe" (optional)
    }
    """
    serializer = UserRegistrationSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.save()
        
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
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Login with email and password.
    
    POST /api/auth/login/
    Body: {
        "email": "user@example.com",
        "password": "password"
    }
    """
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Logout (blacklist refresh token if using blacklist).
    
    POST /api/auth/logout/
    Body: {
        "refresh": "refresh_token_string"
    }
    """
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """
    Get current authenticated user profile.
    
    GET /api/auth/user/
    """
    return Response(UserSerializer(request.user).data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """
    Update user profile.
    
    PATCH /api/auth/user/
    Body: {
        "display_name": "New Name",
        "preferences": {...}
    }
    """
    user = request.user
    serializer = UserSerializer(user, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset(request):
    """
    Request password reset email.
    
    POST /api/auth/password-reset/
    Body: {
        "email": "user@example.com"
    }
    """
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


@api_view(['POST'])
@permission_classes([AllowAny])
def confirm_password_reset(request):
    """
    Confirm password reset with token.
    
    POST /api/auth/password-reset/confirm/
    Body: {
        "token": "reset_token",
        "new_password": "newsecurepassword"
    }
    """
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_email(request):
    """
    Verify email with token.
    
    POST /api/auth/verify-email/
    Body: {
        "token": "verification_token"
    }
    """
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


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_account(request):
    """
    GDPR-compliant account deletion (anonymization).
    
    DELETE /api/auth/user/
    Body: {
        "password": "currentpassword",
        "confirm": true
    }
    """
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