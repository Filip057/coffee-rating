from rest_framework import serializers
from .models import Group, GroupMembership, GroupLibraryEntry
from apps.accounts.models import User
from apps.beans.models import CoffeeBean


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user info for nested serialization."""
    
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'display_name']
        read_only_fields = fields
    
    def get_display_name(self, obj):
        return obj.get_display_name()


class GroupMembershipSerializer(serializers.ModelSerializer):
    """Serializer for group memberships."""
    
    user = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = GroupMembership
        fields = ['id', 'user', 'group', 'role', 'joined_at']
        read_only_fields = ['id', 'joined_at']


class GroupSerializer(serializers.ModelSerializer):
    """Main serializer for groups."""
    
    owner = UserMinimalSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    user_role = serializers.SerializerMethodField()
    
    class Meta:
        model = Group
        fields = [
            'id',
            'name',
            'description',
            'is_private',
            'invite_code',
            'owner',
            'member_count',
            'user_role',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'invite_code', 'owner', 'created_at', 'updated_at']
    
    def get_member_count(self, obj):
        """Get number of members in the group."""
        return obj.memberships.count()
    
    def get_user_role(self, obj):
        """Get current user's role in the group."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.get_user_role(request.user)
        return None


class GroupCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating groups."""
    
    class Meta:
        model = Group
        fields = ['name', 'description', 'is_private']


class GroupListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    
    owner = UserMinimalSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Group
        fields = [
            'id',
            'name',
            'description',
            'is_private',
            'owner',
            'member_count',
            'created_at',
        ]
        read_only_fields = fields
    
    def get_member_count(self, obj):
        return obj.memberships.count()


class GroupMemberSerializer(serializers.ModelSerializer):
    """Detailed member information."""
    
    user = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = GroupMembership
        fields = ['id', 'user', 'role', 'joined_at']
        read_only_fields = fields


class CoffeeBeanMinimalSerializer(serializers.ModelSerializer):
    """Minimal bean info for nested serialization."""
    
    class Meta:
        model = CoffeeBean
        fields = ['id', 'name', 'roastery_name', 'avg_rating', 'review_count']
        read_only_fields = fields


class GroupLibraryEntrySerializer(serializers.ModelSerializer):
    """Serializer for group library entries."""
    
    coffeebean = CoffeeBeanMinimalSerializer(read_only=True)
    added_by = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = GroupLibraryEntry
        fields = [
            'id',
            'group',
            'coffeebean',
            'added_by',
            'added_at',
            'pinned',
            'notes',
        ]
        read_only_fields = ['id', 'added_by', 'added_at']


class JoinGroupSerializer(serializers.Serializer):
    """Serializer for joining a group with invite code."""
    
    invite_code = serializers.CharField(max_length=16, required=True)


class UpdateMemberRoleSerializer(serializers.Serializer):
    """Serializer for updating member role."""
    
    role = serializers.ChoiceField(choices=['admin', 'member'], required=True)