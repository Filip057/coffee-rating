"""
Custom permission classes for purchases app.

This module defines permission classes for controlling access to
purchase records and payment shares.

Created in Phase 3 of purchases app refactoring.
"""
from rest_framework.permissions import BasePermission


class IsGroupMemberForPurchase(BasePermission):
    """
    Permission to check if user is a member of the purchase's group.

    Allows access if:
    - Purchase is personal (no group) and user is the buyer
    - Purchase is in a group and user is a member

    Usage:
        @permission_classes([IsAuthenticated, IsGroupMemberForPurchase])
        class PurchaseRecordViewSet(viewsets.ModelViewSet):
            ...
    """

    message = 'You must be a member of this group to view this purchase.'

    def has_permission(self, request, view):
        """Check permission for create action."""
        if view.action == 'create':
            # Check if creating a group purchase
            group_id = request.data.get('group')
            if group_id:
                # Must be a member of the group
                from apps.groups.models import Group
                try:
                    group = Group.objects.get(id=group_id)
                    if not group.has_member(request.user):
                        self.message = 'You must be a member of this group to create a purchase.'
                        return False
                except Group.DoesNotExist:
                    return False
        return True

    def has_object_permission(self, request, view, obj):
        """Check if user can access the purchase."""
        # Personal purchase - check if user is the buyer
        if not obj.group:
            return obj.bought_by == request.user

        # Group purchase - check if user is a member
        return obj.group.has_member(request.user)


class CanManagePurchase(BasePermission):
    """
    Permission to manage (update/delete) a purchase.

    Allows if:
    - Personal purchase: user is the buyer
    - Group purchase: user is the buyer OR group owner

    Usage:
        def get_permissions(self):
            if self.action in ['update', 'partial_update', 'destroy']:
                return [IsAuthenticated(), CanManagePurchase()]
            return super().get_permissions()
    """

    message = 'You do not have permission to manage this purchase.'

    def has_object_permission(self, request, view, obj):
        """Check if user can manage the purchase."""
        # Personal purchase - must be buyer
        if not obj.group:
            return obj.bought_by == request.user

        # Group purchase - buyer or group owner
        return (
            obj.bought_by == request.user or
            obj.group.owner == request.user
        )


class CanMarkPaymentPaid(BasePermission):
    """
    Permission to mark a payment share as paid.

    Allows if:
    - User has a share in this purchase (marking own payment via reference)
    - User is the purchase buyer (can mark any share)
    - User is the group owner (can mark any share)

    Usage:
        @action(detail=True, methods=['post'])
        @permission_classes([IsAuthenticated, CanMarkPaymentPaid])
        def mark_paid(self, request, pk=None):
            ...
    """

    message = 'You do not have permission to mark this payment as paid.'

    def has_object_permission(self, request, view, obj):
        """Check if user can mark payment as paid."""
        from .models import PaymentShare

        # Determine if obj is a PurchaseRecord or PaymentShare
        if hasattr(obj, 'payment_shares'):
            # This is a PurchaseRecord (from mark_paid action)
            purchase = obj
            # User can mark if they have a share (will be validated by payment_reference)
            if PaymentShare.objects.filter(purchase=purchase, user=request.user).exists():
                return True
        else:
            # This is a PaymentShare - check if user owns this specific share
            purchase = obj.purchase
            if obj.user == request.user:
                return True

        # Purchase buyer can mark any payment
        if purchase.bought_by == request.user:
            return True

        # Group owner can mark any payment in their group
        if purchase.group and purchase.group.owner == request.user:
            return True

        return False


class IsGroupMemberForShare(BasePermission):
    """
    Permission to view a payment share.

    Allows if:
    - User owns the payment share
    - User is a member of the purchase's group
    - User is the buyer of the purchase (personal purchases)

    Usage:
        class PaymentShareViewSet(viewsets.ReadOnlyModelViewSet):
            permission_classes = [IsAuthenticated, IsGroupMemberForShare]
    """

    message = 'You do not have permission to view this payment share.'

    def has_object_permission(self, request, view, obj):
        """Check if user can view the payment share."""
        # User owns the share
        if obj.user == request.user:
            return True

        # User is member of the group
        if obj.purchase.group:
            return obj.purchase.group.has_member(request.user)

        # Personal purchase - only buyer can see
        return obj.purchase.bought_by == request.user
