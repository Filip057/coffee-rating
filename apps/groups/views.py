from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import extend_schema

from .models import Group
from .serializers import (
    GroupSerializer,
    GroupCreateSerializer,
    GroupListSerializer,
    GroupMemberSerializer,
    GroupLibraryEntrySerializer,
    JoinGroupSerializer,
    UpdateMemberRoleSerializer,
)
from .permissions import IsGroupAdmin

from apps.groups.services import (
    create_group,
    delete_group,
    join_group,
    leave_group,
    remove_member,
    get_group_members,
    update_member_role,
    regenerate_invite_code,
    add_to_library,
    get_group_library,
    # Exceptions
    GroupsServiceError,
    InvalidInviteCodeError,
    AlreadyMemberError,
    NotMemberError,
    OwnerCannotLeaveError,
    CannotRemoveOwnerError,
    InsufficientPermissionsError,
    DuplicateLibraryEntryError,
    BeanNotFoundError,
    CannotChangeOwnerRoleError,
)


class GroupPagination(PageNumberPagination):
    """Custom pagination for groups."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class GroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Group CRUD operations.

    All business logic is handled by services.
    Views are thin HTTP handlers only.

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
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsGroupAdmin()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        """Create a new group."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group = create_group(
            name=serializer.validated_data['name'],
            owner=request.user,
            description=serializer.validated_data.get('description', ''),
            is_private=serializer.validated_data.get('is_private', True)
        )

        output_serializer = GroupSerializer(group, context={'request': request})
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """Delete a group."""
        try:
            delete_group(group_id=self.kwargs['pk'], user=request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except InsufficientPermissionsError as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Get all members of the group."""
        memberships = get_group_members(group_id=pk)
        serializer = GroupMemberSerializer(memberships, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Join a group using invite code."""
        serializer = JoinGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            membership = join_group(
                group_id=pk,
                user=request.user,
                invite_code=serializer.validated_data['invite_code']
            )
        except (InvalidInviteCodeError, AlreadyMemberError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        output_serializer = GroupMemberSerializer(membership)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Leave a group."""
        try:
            leave_group(group_id=pk, user=request.user)
            return Response(
                {'message': 'Successfully left the group'},
                status=status.HTTP_204_NO_CONTENT
            )
        except (OwnerCannotLeaveError, NotMemberError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsGroupAdmin])
    def regenerate_invite(self, request, pk=None):
        """Regenerate invite code (admin only)."""
        try:
            new_code = regenerate_invite_code(group_id=pk, user=request.user)
            return Response({
                'invite_code': new_code,
                'message': 'Invite code regenerated successfully'
            })
        except InsufficientPermissionsError as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsGroupAdmin])
    def update_member_role(self, request, pk=None):
        """Update member's role (admin only)."""
        serializer = UpdateMemberRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = request.data.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            membership = update_member_role(
                group_id=pk,
                user_id=user_id,
                new_role=serializer.validated_data['role'],
                updated_by=request.user
            )
        except InsufficientPermissionsError as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except (NotMemberError, CannotChangeOwnerRoleError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        output_serializer = GroupMemberSerializer(membership)
        return Response(output_serializer.data)

    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated, IsGroupAdmin])
    def remove_member(self, request, pk=None):
        """Remove a member from the group (admin only)."""
        user_id = request.data.get('user_id')

        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            remove_member(group_id=pk, user_id=user_id, removed_by=request.user)
            return Response(
                {'message': 'Member removed successfully'},
                status=status.HTTP_204_NO_CONTENT
            )
        except InsufficientPermissionsError as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except (CannotRemoveOwnerError, NotMemberError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def library(self, request, pk=None):
        """Get group's coffee library."""
        try:
            library = get_group_library(group_id=pk, user=request.user)
            serializer = GroupLibraryEntrySerializer(library, many=True)
            return Response(serializer.data)
        except NotMemberError as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=['post'])
    def add_to_library(self, request, pk=None):
        """Add coffee bean to group library."""
        coffeebean_id = request.data.get('coffeebean_id')
        notes = request.data.get('notes', '')

        if not coffeebean_id:
            return Response(
                {'error': 'coffeebean_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            entry = add_to_library(
                group_id=pk,
                coffeebean_id=coffeebean_id,
                user=request.user,
                notes=notes
            )
        except BeanNotFoundError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except (NotMemberError, DuplicateLibraryEntryError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = GroupLibraryEntrySerializer(entry)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(
    responses={200: GroupListSerializer(many=True)},
    description="Get all groups where the current user is a member.",
    tags=['groups'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_groups(request):
    """Get all groups where user is a member."""
    groups = Group.objects.filter(
        memberships__user=request.user
    ).select_related('owner').distinct()

    serializer = GroupListSerializer(groups, many=True, context={'request': request})
    return Response(serializer.data)
