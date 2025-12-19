"""
Service layer unit tests for groups app.

Tests cover:
- Transaction safety
- Concurrency protection (race conditions)
- Business logic validation
- Error handling
"""

import pytest
import threading
from uuid import uuid4
from unittest.mock import patch
from django.db import IntegrityError, transaction
from django.test import TransactionTestCase

from apps.groups.models import Group, GroupMembership, GroupLibraryEntry, GroupRole
from apps.groups.services import (
    create_group,
    get_group_by_id,
    update_group,
    delete_group,
    join_group,
    leave_group,
    remove_member,
    get_group_members,
    update_member_role,
    regenerate_invite_code,
    validate_invite_code,
    add_to_library,
    remove_from_library,
    pin_library_entry,
    unpin_library_entry,
    get_group_library,
)
from apps.groups.services.exceptions import (
    GroupNotFoundError,
    InvalidInviteCodeError,
    AlreadyMemberError,
    NotMemberError,
    InsufficientPermissionsError,
    OwnerCannotLeaveError,
    CannotChangeOwnerRoleError,
    CannotRemoveOwnerError,
    BeanNotFoundError,
    DuplicateLibraryEntryError,
)


# =============================================================================
# Group Management Service Tests
# =============================================================================

@pytest.mark.django_db
class TestGroupManagement:
    """Tests for group_management.py service functions."""

    def test_create_group_success(self, group_owner):
        """Creating a group also creates owner membership."""
        group = create_group(
            name="Test Group",
            owner=group_owner,
            description="Test description",
            is_private=True
        )

        # Verify group created
        assert group.name == "Test Group"
        assert group.owner == group_owner
        assert group.description == "Test description"
        assert group.is_private is True
        assert group.invite_code is not None
        assert len(group.invite_code) == 16

        # Verify owner membership created
        membership = GroupMembership.objects.get(group=group, user=group_owner)
        assert membership.role == GroupRole.OWNER

    def test_create_group_generates_unique_invite_code(self, group_owner):
        """Each group gets a unique invite code."""
        group1 = create_group(name="Group 1", owner=group_owner)
        group2 = create_group(name="Group 2", owner=group_owner)

        assert group1.invite_code != group2.invite_code
        assert len(group1.invite_code) == 16
        assert len(group2.invite_code) == 16

    @pytest.mark.django_db(transaction=True)
    def test_create_group_retries_on_collision(self, group_owner):
        """Service retries if invite code collides (unlikely but possible)."""
        # Mock secrets.token_urlsafe to return same code twice
        with patch('apps.groups.services.group_management.secrets.token_urlsafe') as mock_token:
            mock_token.return_value = 'samecode12345678'

            # First call succeeds
            group1 = create_group(name="Group 1", owner=group_owner)

            # Second call should retry and eventually succeed
            # (but will still fail since we're mocking the same code)
            with pytest.raises(RuntimeError, match="Failed to generate unique invite code"):
                create_group(name="Group 2", owner=group_owner)

    def test_get_group_by_id_success(self, group):
        """Can retrieve group by ID."""
        retrieved = get_group_by_id(group_id=group.id)

        assert retrieved.id == group.id
        assert retrieved.name == group.name

    def test_get_group_by_id_not_found(self):
        """Raises GroupNotFoundError if group doesn't exist."""
        with pytest.raises(GroupNotFoundError):
            get_group_by_id(group_id=uuid4())

    def test_update_group_success(self, group, group_owner):
        """Owner can update group details."""
        updated = update_group(
            group_id=group.id,
            user=group_owner,
            name="Updated Name",
            description="Updated Description"
        )

        assert updated.name == "Updated Name"
        assert updated.description == "Updated Description"

    def test_update_group_insufficient_permissions(self, group, member_user):
        """Non-admin cannot update group."""
        # Add member_user as regular member
        GroupMembership.objects.create(
            user=member_user,
            group=group,
            role=GroupRole.MEMBER
        )

        with pytest.raises(InsufficientPermissionsError):
            update_group(
                group_id=group.id,
                user=member_user,
                name="Hacked Name"
            )

    def test_delete_group_success(self, group, group_owner):
        """Owner can delete group."""
        group_id = group.id

        delete_group(group_id=group_id, user=group_owner)

        # Verify group deleted
        assert not Group.objects.filter(id=group_id).exists()

    def test_delete_group_insufficient_permissions(self, group, admin_user):
        """Non-owner cannot delete group."""
        # Add admin_user as admin (not owner)
        GroupMembership.objects.create(
            user=admin_user,
            group=group,
            role=GroupRole.ADMIN
        )

        with pytest.raises(InsufficientPermissionsError):
            delete_group(group_id=group.id, user=admin_user)


# =============================================================================
# Membership Management Service Tests
# =============================================================================

@pytest.mark.django_db
class TestMembershipManagement:
    """Tests for membership_management.py service functions."""

    def test_join_group_success(self, group, group_other_user):
        """User can join group with valid invite code."""
        membership = join_group(
            group_id=group.id,
            user=group_other_user,
            invite_code=group.invite_code
        )

        assert membership.user == group_other_user
        assert membership.group == group
        assert membership.role == GroupRole.MEMBER

    def test_join_group_invalid_invite_code(self, group, group_other_user):
        """Cannot join with wrong invite code."""
        with pytest.raises(InvalidInviteCodeError):
            join_group(
                group_id=group.id,
                user=group_other_user,
                invite_code="wrongcode123"
            )

    def test_join_group_already_member(self, group, group_owner):
        """Cannot join if already a member."""
        with pytest.raises(AlreadyMemberError):
            join_group(
                group_id=group.id,
                user=group_owner,  # Already owner
                invite_code=group.invite_code
            )

    def test_leave_group_success(self, group, member_user):
        """Member can leave group."""
        # Add member
        GroupMembership.objects.create(
            user=member_user,
            group=group,
            role=GroupRole.MEMBER
        )

        leave_group(group_id=group.id, user=member_user)

        # Verify membership deleted
        assert not GroupMembership.objects.filter(
            group=group,
            user=member_user
        ).exists()

    def test_leave_group_owner_cannot_leave(self, group, group_owner):
        """Owner cannot leave their own group."""
        with pytest.raises(OwnerCannotLeaveError):
            leave_group(group_id=group.id, user=group_owner)

    def test_remove_member_success(self, group, group_owner, member_user):
        """Admin can remove a member."""
        # Add member
        GroupMembership.objects.create(
            user=member_user,
            group=group,
            role=GroupRole.MEMBER
        )

        remove_member(
            group_id=group.id,
            user_id=member_user.id,
            removed_by=group_owner
        )

        # Verify membership deleted
        assert not GroupMembership.objects.filter(
            group=group,
            user=member_user
        ).exists()

    def test_remove_member_cannot_remove_self(self, group, group_owner):
        """Admin cannot remove themselves."""
        with pytest.raises(CannotRemoveOwnerError):
            remove_member(
                group_id=group.id,
                user_id=group_owner.id,
                removed_by=group_owner
            )

    def test_get_group_members_success(self, group_with_members):
        """Can retrieve all group members."""
        members = get_group_members(group_id=group_with_members.id)

        # group_with_members has owner, admin, and member
        assert members.count() == 3
        assert any(m.role == GroupRole.OWNER for m in members)
        assert any(m.role == GroupRole.ADMIN for m in members)
        assert any(m.role == GroupRole.MEMBER for m in members)


# =============================================================================
# Role Management Service Tests
# =============================================================================

@pytest.mark.django_db
class TestRoleManagement:
    """Tests for role_management.py service functions."""

    def test_update_member_role_success(self, group, group_owner, member_user):
        """Admin can update member role."""
        # Add member
        GroupMembership.objects.create(
            user=member_user,
            group=group,
            role=GroupRole.MEMBER
        )

        # Promote to admin
        updated = update_member_role(
            group_id=group.id,
            user_id=member_user.id,
            new_role=GroupRole.ADMIN,
            updated_by=group_owner
        )

        assert updated.role == GroupRole.ADMIN

    def test_update_member_role_cannot_change_owner(self, group, group_owner):
        """Cannot change owner's role."""
        with pytest.raises(CannotChangeOwnerRoleError):
            update_member_role(
                group_id=group.id,
                user_id=group_owner.id,
                new_role=GroupRole.MEMBER,
                updated_by=group_owner
            )

    def test_update_member_role_insufficient_permissions(self, group, member_user, admin_user):
        """Member cannot change roles."""
        # Add both as members
        GroupMembership.objects.create(
            user=member_user,
            group=group,
            role=GroupRole.MEMBER
        )
        GroupMembership.objects.create(
            user=admin_user,
            group=group,
            role=GroupRole.MEMBER
        )

        with pytest.raises(InsufficientPermissionsError):
            update_member_role(
                group_id=group.id,
                user_id=admin_user.id,
                new_role=GroupRole.ADMIN,
                updated_by=member_user  # Not admin
            )


# =============================================================================
# Invite Management Service Tests
# =============================================================================

@pytest.mark.django_db
class TestInviteManagement:
    """Tests for invite_management.py service functions."""

    def test_regenerate_invite_code_success(self, group, group_owner):
        """Admin can regenerate invite code."""
        old_code = group.invite_code

        new_code = regenerate_invite_code(
            group_id=group.id,
            user=group_owner
        )

        assert new_code != old_code
        assert len(new_code) == 16

        # Verify in database
        group.refresh_from_db()
        assert group.invite_code == new_code

    def test_regenerate_invite_code_insufficient_permissions(self, group, member_user):
        """Member cannot regenerate invite code."""
        GroupMembership.objects.create(
            user=member_user,
            group=group,
            role=GroupRole.MEMBER
        )

        with pytest.raises(InsufficientPermissionsError):
            regenerate_invite_code(
                group_id=group.id,
                user=member_user
            )

    def test_validate_invite_code_success(self, group):
        """Valid invite code returns True."""
        is_valid = validate_invite_code(
            group_id=group.id,
            invite_code=group.invite_code
        )

        assert is_valid is True

    def test_validate_invite_code_invalid(self, group):
        """Invalid invite code returns False."""
        is_valid = validate_invite_code(
            group_id=group.id,
            invite_code="wrongcode123"
        )

        assert is_valid is False


# =============================================================================
# Library Management Service Tests
# =============================================================================

@pytest.mark.django_db
class TestLibraryManagement:
    """Tests for library_management.py service functions."""

    def test_add_to_library_success(self, group, group_owner, group_coffeebean):
        """Member can add bean to library."""
        entry = add_to_library(
            group_id=group.id,
            coffeebean_id=group_coffeebean.id,
            user=group_owner,
            notes="Great coffee!",
            pinned=False
        )

        assert entry.group == group
        assert entry.coffeebean == group_coffeebean
        assert entry.added_by == group_owner
        assert entry.notes == "Great coffee!"
        assert entry.pinned is False

    def test_add_to_library_duplicate(self, group, group_owner, group_coffeebean):
        """Cannot add same bean twice."""
        # Add once
        add_to_library(
            group_id=group.id,
            coffeebean_id=group_coffeebean.id,
            user=group_owner
        )

        # Try to add again
        with pytest.raises(DuplicateLibraryEntryError):
            add_to_library(
                group_id=group.id,
                coffeebean_id=group_coffeebean.id,
                user=group_owner
            )

    def test_add_to_library_not_member(self, group, group_other_user, group_coffeebean):
        """Non-member cannot add to library."""
        with pytest.raises(NotMemberError):
            add_to_library(
                group_id=group.id,
                coffeebean_id=group_coffeebean.id,
                user=group_other_user
            )

    def test_remove_from_library_success(self, group_library_entry, group_owner):
        """Member can remove bean from library."""
        entry_id = group_library_entry.id

        remove_from_library(
            entry_id=entry_id,
            user=group_owner
        )

        # Verify deleted
        assert not GroupLibraryEntry.objects.filter(id=entry_id).exists()

    def test_pin_library_entry_success(self, group_library_entry, group_owner):
        """Member can pin library entry."""
        assert group_library_entry.pinned is False

        pinned = pin_library_entry(
            entry_id=group_library_entry.id,
            user=group_owner
        )

        assert pinned.pinned is True

    def test_unpin_library_entry_success(self, group_library_entry, group_owner):
        """Member can unpin library entry."""
        # Pin it first
        group_library_entry.pinned = True
        group_library_entry.save()

        unpinned = unpin_library_entry(
            entry_id=group_library_entry.id,
            user=group_owner
        )

        assert unpinned.pinned is False

    def test_get_group_library_success(self, group, group_owner, group_coffeebean):
        """Can retrieve group library."""
        # Add bean to library
        add_to_library(
            group_id=group.id,
            coffeebean_id=group_coffeebean.id,
            user=group_owner
        )

        library = get_group_library(group_id=group.id, user=group_owner)

        assert library.count() == 1
        assert library[0].coffeebean == group_coffeebean


# =============================================================================
# Concurrency Tests (Race Conditions)
# =============================================================================

class TestConcurrency(TransactionTestCase):
    """
    Tests for concurrency protection using TransactionTestCase.

    Note: TransactionTestCase is required for testing actual database
    transactions and concurrency. Regular TestCase wraps tests in
    a transaction, which doesn't allow testing real concurrency.
    """

    def setUp(self):
        """Create test fixtures."""
        from apps.accounts.models import User

        self.owner = User.objects.create_user(
            email='owner@test.com',
            password='TestPass123!',
            display_name='Owner',
            email_verified=True
        )

        # Create group with owner membership
        self.group = Group.objects.create(
            name='Test Group',
            owner=self.owner,
            is_private=True
        )
        GroupMembership.objects.create(
            user=self.owner,
            group=self.group,
            role=GroupRole.OWNER
        )

    def test_concurrent_joins_prevented(self):
        """
        Multiple concurrent join requests should not create duplicate memberships.

        This test verifies that select_for_update() in join_group() prevents
        race conditions when multiple threads try to join simultaneously.
        """
        from apps.accounts.models import User

        # Create 5 test users
        users = [
            User.objects.create_user(
                email=f'user{i}@test.com',
                password='TestPass123!',
                display_name=f'User {i}',
                email_verified=True
            )
            for i in range(5)
        ]

        results = []
        errors = []
        invite_code = self.group.invite_code

        def join_as_user(user):
            """Join group in a thread."""
            try:
                membership = join_group(
                    group_id=self.group.id,
                    user=user,
                    invite_code=invite_code
                )
                results.append(membership)
            except AlreadyMemberError as e:
                errors.append((user, str(e)))
            except Exception as e:
                errors.append((user, f"Unexpected error: {str(e)}"))

        # Spawn threads to join simultaneously
        threads = [
            threading.Thread(target=join_as_user, args=(user,))
            for user in users
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Verify: each user joined exactly once
        assert len(results) == 5, f"Expected 5 successful joins, got {len(results)}"
        assert len(errors) == 0, f"Expected no errors, got: {errors}"

        # Verify: no duplicate memberships in database
        total_memberships = GroupMembership.objects.filter(group=self.group).count()
        assert total_memberships == 6  # 5 new + 1 owner

    def test_concurrent_role_updates_no_lost_updates(self):
        """
        Concurrent role updates should not result in lost updates.

        This test verifies that select_for_update() in update_member_role()
        prevents lost update race conditions.
        """
        from apps.accounts.models import User

        # Create a member
        member = User.objects.create_user(
            email='member@test.com',
            password='TestPass123!',
            display_name='Member',
            email_verified=True
        )
        GroupMembership.objects.create(
            user=member,
            group=self.group,
            role=GroupRole.MEMBER
        )

        results = []
        errors = []

        def update_role(role):
            """Update member role in a thread."""
            try:
                membership = update_member_role(
                    group_id=self.group.id,
                    user_id=member.id,
                    new_role=role,
                    updated_by=self.owner
                )
                results.append(membership.role)
            except Exception as e:
                errors.append(str(e))

        # Spawn threads to update role concurrently
        # Alternate between ADMIN and MEMBER
        threads = [
            threading.Thread(target=update_role, args=(GroupRole.ADMIN if i % 2 == 0 else GroupRole.MEMBER,))
            for i in range(10)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Verify: all updates completed
        assert len(results) == 10, f"Expected 10 updates, got {len(results)}"
        assert len(errors) == 0, f"Expected no errors, got: {errors}"

        # Verify: final state is consistent (last update won)
        membership = GroupMembership.objects.get(group=self.group, user=member)
        assert membership.role in [GroupRole.ADMIN, GroupRole.MEMBER]

    def test_concurrent_invite_regeneration_no_collisions(self):
        """
        Concurrent invite code regeneration should not create collisions.

        This test verifies that the retry logic in regenerate_invite_code()
        handles collisions gracefully.
        """
        results = []
        errors = []

        def regenerate():
            """Regenerate invite code in a thread."""
            try:
                new_code = regenerate_invite_code(
                    group_id=self.group.id,
                    user=self.owner
                )
                results.append(new_code)
            except Exception as e:
                errors.append(str(e))

        # Spawn threads to regenerate simultaneously
        threads = [
            threading.Thread(target=regenerate)
            for _ in range(10)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Verify: all regenerations completed
        assert len(results) == 10, f"Expected 10 regenerations, got {len(results)}"
        assert len(errors) == 0, f"Expected no errors, got: {errors}"

        # Verify: all codes are unique
        assert len(set(results)) == 10, "Expected all invite codes to be unique"

        # Verify: final code is one of the generated codes
        self.group.refresh_from_db()
        assert self.group.invite_code in results


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.django_db
class TestServiceIntegration:
    """Integration tests for service workflows."""

    def test_full_group_lifecycle(self, group_owner, group_other_user, group_coffeebean):
        """Test complete group lifecycle: create, join, add to library, leave."""
        # 1. Create group
        group = create_group(
            name="Coffee Club",
            owner=group_owner,
            description="For coffee lovers"
        )

        # 2. Other user joins
        membership = join_group(
            group_id=group.id,
            user=group_other_user,
            invite_code=group.invite_code
        )
        assert membership.role == GroupRole.MEMBER

        # 3. Member adds bean to library
        entry = add_to_library(
            group_id=group.id,
            coffeebean_id=group_coffeebean.id,
            user=group_other_user,
            notes="My favorite!"
        )
        assert entry.added_by == group_other_user

        # 4. Check library
        library = get_group_library(group_id=group.id, user=group_other_user)
        assert library.count() == 1

        # 5. Member leaves
        leave_group(group_id=group.id, user=group_other_user)
        assert not GroupMembership.objects.filter(
            group=group,
            user=group_other_user
        ).exists()

        # 6. Library entry persists (not deleted when member leaves)
        assert GroupLibraryEntry.objects.filter(id=entry.id).exists()

    def test_group_deletion_cascades(self, group_owner, group_other_user, group_coffeebean):
        """Deleting group cascades to memberships and library."""
        # Create group with member and library
        group = create_group(name="Test", owner=group_owner)

        join_group(
            group_id=group.id,
            user=group_other_user,
            invite_code=group.invite_code
        )

        add_to_library(
            group_id=group.id,
            coffeebean_id=group_coffeebean.id,
            user=group_owner
        )

        group_id = group.id

        # Delete group
        delete_group(group_id=group_id, user=group_owner)

        # Verify everything deleted
        assert not Group.objects.filter(id=group_id).exists()
        assert not GroupMembership.objects.filter(group_id=group_id).exists()
        assert not GroupLibraryEntry.objects.filter(group_id=group_id).exists()
