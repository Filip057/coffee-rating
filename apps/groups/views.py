from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import Group, GroupMembership, GroupLibraryEntry, GroupRole
from .serializers import (
    GroupSerializer,
    GroupCreateSerializer,
    GroupListSerializer,
    GroupMemberSerializer,
    GroupLibraryEntrySerializer,
    JoinGroupSerializer,
    UpdateMemberRoleSerializer,
)
from .permissions import IsGroupAdmin, IsGroupMember
from apps.beans.models import CoffeeBean


class GroupPagination(PageNumberPagination):
    """Custom pagination for groups."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class GroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Group CRUD operations.
    
    list: Get all groups (user is member of)
    create: Create a new group
    retrieve: Get a specific group
    update: Update a group (admin only)
    partial_update: Partially update a group (admin only)
    destroy: Delete a group (owner only)
    """
    
    queryset = Group.objects.select_related('owner').prefetch_related('memberships')
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = GroupPagination
    
    def get_queryset(self):
        """Return only groups where user is a member."""
        user = self.request.user
        return Group.objects.filter(
            memberships__user=user
        ).select_related('owner').prefetch_related('memberships').distinct()
    
    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action == 'list':
            return GroupListSerializer
        elif self.action == 'create':
            return GroupCreateSerializer
        return GroupSerializer
    
    def get_permissions(self):
        """Set permissions based on action."""
        if self.action in ['update', 'partial_update']:
            return [IsAuthenticated(), IsGroupAdmin()]
        elif self.action == 'destroy':
            return [IsAuthenticated(), IsGroupAdmin()]
        return [IsAuthenticated()]
    
    @transaction.atomic
    def perform_create(self, serializer):
        """
        Create group and add creator as owner.
        """
        group = serializer.save(owner=self.request.user)
        
        # Add creator as owner member
        GroupMembership.objects.create(
            user=self.request.user,
            group=group,
            role=GroupRole.OWNER
        )
    
    def perform_destroy(self, instance):
        """Delete group (owner only)."""
        if instance.owner != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only the group owner can delete the group")
        instance.delete()
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """
        Get all members of the group.
        
        GET /api/groups/{id}/members/
        """
        group = self.get_object()
        memberships = group.memberships.select_related('user').order_by('-role', 'joined_at')
        serializer = GroupMemberSerializer(memberships, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """
        Join a group using invite code.
        
        POST /api/groups/{id}/join/
        Body: {"invite_code": "abc123"}
        """
        group = self.get_object()
        serializer = JoinGroupSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        invite_code = serializer.validated_data['invite_code']
        
        # Verify invite code
        if group.invite_code != invite_code:
            return Response(
                {'error': 'Invalid invite code'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already a member
        if group.has_member(request.user):
            return Response(
                {'error': 'You are already a member of this group'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add user as member
        membership = GroupMembership.objects.create(
            user=request.user,
            group=group,
            role=GroupRole.MEMBER
        )
        
        return Response(
            GroupMemberSerializer(membership).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """
        Leave a group.
        
        POST /api/groups/{id}/leave/
        """
        group = self.get_object()
        
        # Owner cannot leave their own group
        if group.owner == request.user:
            return Response(
                {'error': 'Group owner cannot leave. Transfer ownership or delete the group.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if member
        try:
            membership = GroupMembership.objects.get(user=request.user, group=group)
            membership.delete()
            return Response(
                {'message': 'Successfully left the group'},
                status=status.HTTP_204_NO_CONTENT
            )
        except GroupMembership.DoesNotExist:
            return Response(
                {'error': 'You are not a member of this group'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def regenerate_invite(self, request, pk=None):
        """
        Regenerate invite code (admin only).
        
        POST /api/groups/{id}/regenerate_invite/
        """
        group = self.get_object()
        
        # Check if user is admin
        if not group.is_admin(request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only admins can regenerate invite codes")
        
        new_code = group.regenerate_invite_code()
        
        return Response({
            'invite_code': new_code,
            'message': 'Invite code regenerated successfully'
        })
    
    @action(detail=True, methods=['post'])
    def update_member_role(self, request, pk=None):
        """
        Update member's role (admin only).
        
        POST /api/groups/{id}/update_member_role/
        Body: {"user_id": "uuid", "role": "admin" or "member"}
        """
        group = self.get_object()
        
        # Check if requester is admin
        if not group.is_admin(request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only admins can update member roles")
        
        user_id = request.data.get('user_id')
        new_role = request.data.get('role')
        
        if not user_id or not new_role:
            return Response(
                {'error': 'user_id and role are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate role
        serializer = UpdateMemberRoleSerializer(data={'role': new_role})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Get membership
        try:
            membership = GroupMembership.objects.get(group=group, user_id=user_id)
        except GroupMembership.DoesNotExist:
            return Response(
                {'error': 'User is not a member of this group'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Cannot change owner's role
        if membership.role == GroupRole.OWNER:
            return Response(
                {'error': 'Cannot change owner role'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update role
        membership.role = new_role
        membership.save(update_fields=['role'])
        
        return Response(GroupMemberSerializer(membership).data)
    
    @action(detail=True, methods=['delete'])
    def remove_member(self, request, pk=None):
        """
        Remove a member from the group (admin only).
        
        DELETE /api/groups/{id}/remove_member/
        Body: {"user_id": "uuid"}
        """
        group = self.get_object()
        
        # Check if requester is admin
        if not group.is_admin(request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only admins can remove members")
        
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Cannot remove owner
        if str(group.owner.id) == str(user_id):
            return Response(
                {'error': 'Cannot remove group owner'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Remove membership
        try:
            membership = GroupMembership.objects.get(group=group, user_id=user_id)
            membership.delete()
            return Response(
                {'message': 'Member removed successfully'},
                status=status.HTTP_204_NO_CONTENT
            )
        except GroupMembership.DoesNotExist:
            return Response(
                {'error': 'User is not a member of this group'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def library(self, request, pk=None):
        """
        Get group's coffee library.
        
        GET /api/groups/{id}/library/
        """
        group = self.get_object()
        
        # Check if user is member
        if not group.has_member(request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You must be a member to view the group library")
        
        library = GroupLibraryEntry.objects.filter(
            group=group
        ).select_related('coffeebean', 'added_by').order_by('-pinned', '-added_at')
        
        serializer = GroupLibraryEntrySerializer(library, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_to_library(self, request, pk=None):
        """
        Add coffee bean to group library.
        
        POST /api/groups/{id}/add_to_library/
        Body: {"coffeebean_id": "uuid", "notes": "optional"}
        """
        group = self.get_object()
        
        # Check if user is member
        if not group.has_member(request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You must be a member to add to the library")
        
        coffeebean_id = request.data.get('coffeebean_id')
        notes = request.data.get('notes', '')
        
        if not coffeebean_id:
            return Response(
                {'error': 'coffeebean_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            coffeebean = CoffeeBean.objects.get(id=coffeebean_id, is_active=True)
        except CoffeeBean.DoesNotExist:
            return Response(
                {'error': 'Coffee bean not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create or get library entry
        entry, created = GroupLibraryEntry.objects.get_or_create(
            group=group,
            coffeebean=coffeebean,
            defaults={
                'added_by': request.user,
                'notes': notes
            }
        )
        
        if not created:
            return Response(
                {'error': 'Coffee bean already in group library'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = GroupLibraryEntrySerializer(entry)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_groups(request):
    """
    Get all groups where user is a member.
    
    GET /api/groups/my/
    """
    groups = Group.objects.filter(
        memberships__user=request.user
    ).select_related('owner').distinct()
    
    serializer = GroupListSerializer(groups, many=True, context={'request': request})
    return Response(serializer.data)