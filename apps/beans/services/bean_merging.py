"""Bean merging service with full transaction safety."""

from django.db import transaction
from django.contrib.auth import get_user_model
from uuid import UUID

from ..models import CoffeeBean, CoffeeBeanVariant, MergeHistory
from .exceptions import InvalidMergeError, BeanNotFoundError
from .rating_aggregation import update_bean_rating

User = get_user_model()


@transaction.atomic
def merge_beans(
    *,
    source_bean_id: UUID,
    target_bean_id: UUID,
    merged_by: User,
    reason: str = ''
) -> CoffeeBean:
    """
    Merge source bean into target bean with full concurrency protection.

    Process:
    1. Lock both beans
    2. Move all variants from source to target
    3. Update all reviews to point to target
    4. Update all purchases to point to target
    5. Update all library entries (handle duplicates)
    6. Recalculate target's aggregate rating
    7. Create merge history record
    8. Soft delete source bean

    Args:
        source_bean_id: Bean to be merged (will be soft-deleted)
        target_bean_id: Bean to merge into (will be kept)
        merged_by: User performing the merge
        reason: Optional reason for merge

    Returns:
        Updated target bean

    Raises:
        BeanNotFoundError: If either bean doesn't exist
        InvalidMergeError: If merge parameters are invalid
    """
    # Validate inputs
    if source_bean_id == target_bean_id:
        raise InvalidMergeError("Cannot merge bean with itself")

    # Lock both beans to prevent concurrent modifications
    try:
        source = (
            CoffeeBean.objects
            .select_for_update()
            .get(id=source_bean_id)
        )
    except CoffeeBean.DoesNotExist:
        raise BeanNotFoundError(f"Source bean {source_bean_id} not found")

    try:
        target = (
            CoffeeBean.objects
            .select_for_update()
            .get(id=target_bean_id)
        )
    except CoffeeBean.DoesNotExist:
        raise BeanNotFoundError(f"Target bean {target_bean_id} not found")

    # Step 1: Move variants (handle duplicates)
    source_variants = CoffeeBeanVariant.objects.filter(coffeebean=source)
    for variant in source_variants:
        # Check if target already has this weight
        existing = CoffeeBeanVariant.objects.filter(
            coffeebean=target,
            package_weight_grams=variant.package_weight_grams
        ).first()

        if existing:
            # Keep variant with lower price per gram
            if variant.price_per_gram < existing.price_per_gram:
                existing.delete()
                variant.coffeebean = target
                variant.save()
            else:
                variant.delete()
        else:
            variant.coffeebean = target
            variant.save()

    # Step 2: Update reviews
    from apps.reviews.models import Review
    Review.objects.filter(coffeebean=source).update(coffeebean=target)

    # Step 3: Update purchases
    from apps.purchases.models import PurchaseRecord
    PurchaseRecord.objects.filter(coffeebean=source).update(coffeebean=target)

    # Step 4: Update library entries
    from apps.reviews.models import UserLibraryEntry
    from apps.groups.models import GroupLibraryEntry

    # User libraries - handle duplicates
    user_libs = UserLibraryEntry.objects.filter(coffeebean=source)
    for lib in user_libs:
        target_lib = UserLibraryEntry.objects.filter(
            user=lib.user,
            coffeebean=target
        ).first()

        if target_lib:
            # Keep the older entry
            lib.delete()
        else:
            lib.coffeebean = target
            lib.save()

    # Group libraries - handle duplicates
    group_libs = GroupLibraryEntry.objects.filter(coffeebean=source)
    for lib in group_libs:
        target_lib = GroupLibraryEntry.objects.filter(
            group=lib.group,
            coffeebean=target
        ).first()

        if target_lib:
            # Merge notes if any
            if lib.notes and not target_lib.notes:
                target_lib.notes = lib.notes
                target_lib.save()
            lib.delete()
        else:
            lib.coffeebean = target
            lib.save()

    # Step 5: Recalculate target's aggregate rating
    update_bean_rating(bean_id=target.id)
    target.refresh_from_db()

    # Step 6: Create merge history
    MergeHistory.objects.create(
        merged_from=source.id,
        merged_into=target,
        merged_by=merged_by,
        reason=reason
    )

    # Step 7: Soft delete source
    source.is_active = False
    source.name = f"[MERGED] {source.name}"
    source.save(update_fields=['is_active', 'name', 'updated_at'])

    return target
