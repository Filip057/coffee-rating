from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User

"""
How to solve when restoring password, how validate existing email 
"""



class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer for profile display."""
    
    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'display_name',
            'email_verified',
            'created_at',
            'last_login',
            'preferences',
        ]
        read_only_fields = ['id', 'email', 'email_verified', 'created_at', 'last_login']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = ['email', 'password', 'password_confirm', 'display_name']
    
    def validate(self, attrs):
        """Validate password confirmation."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Passwords do not match'
            })
        return attrs
    
    def create(self, validated_data):
        """Create user with hashed password."""
        validated_data.pop('password_confirm')
        
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            display_name=validated_data.get('display_name', '')
        )
        
        # Generate verification token
        import secrets
        user.verification_token = secrets.token_urlsafe(32)
        user.save(update_fields=['verification_token'])
        
        # TODO: Send verification email
        
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request."""
    
    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation."""
    
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        """Validate password confirmation."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'Passwords do not match'
            })
        return attrs


class UserPublicSerializer(serializers.ModelSerializer):
    """Public user info (for displaying in groups, reviews, etc.)."""
    
    class Meta:
        model = User
        fields = ['id', 'display_name', 'created_at']
        read_only_fields = fields