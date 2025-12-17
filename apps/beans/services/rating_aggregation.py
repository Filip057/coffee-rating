"""Rating aggregation service with concurrency protection."""

from django.db import transaction
from django.db.models import Avg, Count
from decimal import Decimal
from uuid import UUID

from ..models import CoffeeBean
from .exceptions import BeanNotFoundError


@transaction.atomic
def update_bean_rating(*, bean_id: UUID) -> CoffeeBean:
    """
    Recalculate and update bean's aggregate rating.

    Uses select_for_update() to prevent race conditions
    when multiple reviews are created/updated simultaneously.

    Args:
        bean_id: Bean UUID

    Returns:
        Updated CoffeeBean instance

    Raises:
        BeanNotFoundError: If bean doesn't exist
    """
    try:
        # Lock the bean to prevent concurrent updates
        bean = (
            CoffeeBean.objects
            .select_for_update()
            .get(id=bean_id)
        )
    except CoffeeBean.DoesNotExist:
        raise BeanNotFoundError(f"Bean {bean_id} not found")

    # Calculate aggregates from reviews
    aggregates = bean.reviews.aggregate(
        avg=Avg('rating'),
        count=Count('id')
    )

    # Update bean
    bean.avg_rating = aggregates['avg'] or Decimal('0.00')
    bean.review_count = aggregates['count']
    bean.save(update_fields=['avg_rating', 'review_count', 'updated_at'])

    return bean


def get_top_rated_beans(*, limit: int = 10, min_reviews: int = 3):
    """
    Get top-rated beans with minimum review count.

    Args:
        limit: Number of beans to return
        min_reviews: Minimum number of reviews required

    Returns:
        QuerySet of top-rated beans
    """
    return (
        CoffeeBean.objects
        .filter(is_active=True, review_count__gte=min_reviews)
        .order_by('-avg_rating', '-review_count')[:limit]
    )


def get_most_reviewed_beans(*, limit: int = 10):
    """
    Get beans with most reviews.

    Args:
        limit: Number of beans to return

    Returns:
        QuerySet of most-reviewed beans
    """
    return (
        CoffeeBean.objects
        .filter(is_active=True)
        .order_by('-review_count', '-avg_rating')[:limit]
    )
