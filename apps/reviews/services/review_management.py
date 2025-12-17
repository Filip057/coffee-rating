"""Review management service - CRUD operations for reviews."""

from django.db import transaction, IntegrityError
from django.db.models import QuerySet
from uuid import UUID
from typing import Optional

from apps.accounts.models import User
from apps.beans.models import CoffeeBean
from apps.groups.models import Group
from apps.reviews.models import Review, Tag
from .exceptions import (
    ReviewNotFoundError,
    DuplicateReviewError,
    InvalidRatingError,
    BeanNotFoundError,
    UnauthorizedReviewActionError,
    InvalidContextError,
    GroupMembershipRequiredError,
)


@transaction.atomic
def create_review(
    *,
    author: User,
    coffeebean_id: UUID,
    rating: int,
    aroma_score: Optional[int] = None,
    flavor_score: Optional[int] = None,
    acidity_score: Optional[int] = None,
    body_score: Optional[int] = None,
    aftertaste_score: Optional[int] = None,
    notes: str = '',
    brew_method: str = '',
    taste_tag_ids: Optional[list[UUID]] = None,
    context: str = 'personal',
    group_id: Optional[UUID] = None,
    would_buy_again: Optional[bool] = None
) -> Review:
    """
    Create a new review for a coffee bean.

    This operation:
    1. Validates rating range
    2. Validates context and group requirements
    3. Checks for duplicate review (author, coffeebean)
    4. Creates review with tags atomically
    5. Auto-creates library entry (handled by caller)

    Args:
        author: User creating the review
        coffeebean_id: UUID of coffee bean being reviewed
        rating: Overall rating (1-5, required)
        aroma_score: Aroma rating (1-5, optional)
        flavor_score: Flavor rating (1-5, optional)
        acidity_score: Acidity rating (1-5, optional)
        body_score: Body rating (1-5, optional)
        aftertaste_score: Aftertaste rating (1-5, optional)
        notes: Written review notes
        brew_method: Brewing method used
        taste_tag_ids: List of tag UUIDs to associate
        context: Review context (personal/group/public)
        group_id: Required if context='group'
        would_buy_again: Purchase intent

    Returns:
        Created Review instance

    Raises:
        InvalidRatingError: If rating not in 1-5 range
        BeanNotFoundError: If coffee bean doesn't exist or inactive
        DuplicateReviewError: If user already reviewed this bean
        InvalidContextError: If group context but no group_id
        GroupMembershipRequiredError: If not member of specified group
    """
    # Validate rating
    if not (1 <= rating <= 5):
        raise InvalidRatingError("Rating must be between 1 and 5")

    # Validate optional scores
    for score_name, score_value in [
        ('aroma', aroma_score),
        ('flavor', flavor_score),
        ('acidity', acidity_score),
        ('body', body_score),
        ('aftertaste', aftertaste_score),
    ]:
        if score_value is not None and not (1 <= score_value <= 5):
            raise InvalidRatingError(f"{score_name.capitalize()} score must be between 1 and 5")

    # Validate coffee bean exists and is active
    try:
        coffeebean = CoffeeBean.objects.get(id=coffeebean_id, is_active=True)
    except CoffeeBean.DoesNotExist:
        raise BeanNotFoundError("Coffee bean not found or inactive")

    # Validate group context
    group = None
    if context == 'group':
        if not group_id:
            raise InvalidContextError("Group ID required for group context reviews")

        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            raise InvalidContextError("Group not found")

        # Check group membership
        if not group.has_member(author):
            raise GroupMembershipRequiredError(
                "You must be a member of this group to create a group review"
            )

    # Check for duplicate review (one per user per bean)
    existing = Review.objects.filter(author=author, coffeebean=coffeebean).exists()
    if existing:
        raise DuplicateReviewError(
            "You have already reviewed this coffee bean. Please update your existing review instead."
        )

    # Create review
    try:
        review = Review.objects.create(
            coffeebean=coffeebean,
            author=author,
            rating=rating,
            aroma_score=aroma_score,
            flavor_score=flavor_score,
            acidity_score=acidity_score,
            body_score=body_score,
            aftertaste_score=aftertaste_score,
            notes=notes,
            brew_method=brew_method,
            context=context,
            group=group,
            would_buy_again=would_buy_again,
        )
    except IntegrityError:
        # Database unique constraint caught duplicate
        raise DuplicateReviewError(
            "You have already reviewed this coffee bean"
        )

    # Associate taste tags
    if taste_tag_ids:
        tags = Tag.objects.filter(id__in=taste_tag_ids)
        review.taste_tags.set(tags)

    return review


def get_review_by_id(*, review_id: UUID) -> Review:
    """
    Retrieve a review by ID.

    Args:
        review_id: UUID of review

    Returns:
        Review instance with related data

    Raises:
        ReviewNotFoundError: If review doesn't exist
    """
    try:
        review = Review.objects.select_related(
            'author',
            'coffeebean',
            'group'
        ).prefetch_related('taste_tags').get(id=review_id)
    except Review.DoesNotExist:
        raise ReviewNotFoundError("Review not found")

    return review


@transaction.atomic
def update_review(
    *,
    review_id: UUID,
    user: User,
    rating: Optional[int] = None,
    aroma_score: Optional[int] = None,
    flavor_score: Optional[int] = None,
    acidity_score: Optional[int] = None,
    body_score: Optional[int] = None,
    aftertaste_score: Optional[int] = None,
    notes: Optional[str] = None,
    brew_method: Optional[str] = None,
    taste_tag_ids: Optional[list[UUID]] = None,
    would_buy_again: Optional[bool] = None
) -> Review:
    """
    Update an existing review.

    Only the review author can update their review.
    Coffeebean, author, context, and group cannot be changed.

    Args:
        review_id: UUID of review to update
        user: User making the update (must be author)
        rating: New overall rating (1-5)
        aroma_score: New aroma rating (1-5)
        flavor_score: New flavor rating (1-5)
        acidity_score: New acidity rating (1-5)
        body_score: New body rating (1-5)
        aftertaste_score: New aftertaste rating (1-5)
        notes: New review notes
        brew_method: New brew method
        taste_tag_ids: New list of tag UUIDs
        would_buy_again: New purchase intent

    Returns:
        Updated Review instance

    Raises:
        ReviewNotFoundError: If review doesn't exist
        UnauthorizedReviewActionError: If user is not the author
        InvalidRatingError: If rating not in 1-5 range
    """
    # Get review with row lock
    try:
        review = (
            Review.objects
            .select_for_update()
            .get(id=review_id)
        )
    except Review.DoesNotExist:
        raise ReviewNotFoundError("Review not found")

    # Check authorization
    if review.author != user:
        raise UnauthorizedReviewActionError(
            "You can only update your own reviews"
        )

    # Validate ratings if provided
    if rating is not None and not (1 <= rating <= 5):
        raise InvalidRatingError("Rating must be between 1 and 5")

    for score_name, score_value in [
        ('aroma', aroma_score),
        ('flavor', flavor_score),
        ('acidity', acidity_score),
        ('body', body_score),
        ('aftertaste', aftertaste_score),
    ]:
        if score_value is not None and not (1 <= score_value <= 5):
            raise InvalidRatingError(f"{score_name.capitalize()} score must be between 1 and 5")

    # Update fields if provided
    if rating is not None:
        review.rating = rating
    if aroma_score is not None:
        review.aroma_score = aroma_score
    if flavor_score is not None:
        review.flavor_score = flavor_score
    if acidity_score is not None:
        review.acidity_score = acidity_score
    if body_score is not None:
        review.body_score = body_score
    if aftertaste_score is not None:
        review.aftertaste_score = aftertaste_score
    if notes is not None:
        review.notes = notes
    if brew_method is not None:
        review.brew_method = brew_method
    if would_buy_again is not None:
        review.would_buy_again = would_buy_again

    review.save()

    # Update tags if provided
    if taste_tag_ids is not None:
        tags = Tag.objects.filter(id__in=taste_tag_ids)
        review.taste_tags.set(tags)

    return review


@transaction.atomic
def delete_review(*, review_id: UUID, user: User) -> None:
    """
    Delete a review.

    Only the review author can delete their review.

    Args:
        review_id: UUID of review to delete
        user: User making the deletion (must be author)

    Raises:
        ReviewNotFoundError: If review doesn't exist
        UnauthorizedReviewActionError: If user is not the author
    """
    # Get review with row lock
    try:
        review = (
            Review.objects
            .select_for_update()
            .get(id=review_id)
        )
    except Review.DoesNotExist:
        raise ReviewNotFoundError("Review not found")

    # Check authorization
    if review.author != user:
        raise UnauthorizedReviewActionError(
            "You can only delete your own reviews"
        )

    # Delete review (CASCADE will handle tags M2M)
    review.delete()


def get_user_reviews(
    *,
    user: User,
    coffeebean_id: Optional[UUID] = None,
    group_id: Optional[UUID] = None,
    rating: Optional[int] = None,
    min_rating: Optional[int] = None,
    context: Optional[str] = None
) -> QuerySet[Review]:
    """
    Get all reviews by a specific user with optional filters.

    Args:
        user: User whose reviews to retrieve
        coffeebean_id: Filter by specific coffee bean
        group_id: Filter by specific group
        rating: Filter by exact rating
        min_rating: Filter by minimum rating
        context: Filter by context (personal/group/public)

    Returns:
        QuerySet of Review instances
    """
    queryset = Review.objects.filter(author=user).select_related(
        'coffeebean',
        'group'
    ).prefetch_related('taste_tags')

    if coffeebean_id:
        queryset = queryset.filter(coffeebean_id=coffeebean_id)

    if group_id:
        queryset = queryset.filter(group_id=group_id)

    if rating:
        queryset = queryset.filter(rating=rating)

    if min_rating:
        queryset = queryset.filter(rating__gte=min_rating)

    if context:
        queryset = queryset.filter(context=context)

    return queryset.order_by('-created_at')
