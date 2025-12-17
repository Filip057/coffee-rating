"""Statistics service - Review analytics and aggregations."""

from django.db.models import Count, Avg
from django.db.models.functions import TruncMonth
from uuid import UUID
from typing import Optional

from apps.reviews.models import Review, Tag
from apps.beans.models import CoffeeBean
from .exceptions import BeanNotFoundError


def get_review_statistics(
    *,
    user_id: Optional[UUID] = None,
    bean_id: Optional[UUID] = None
) -> dict:
    """
    Calculate comprehensive review statistics.

    Can be filtered by user or bean to get specific statistics.
    Useful for dashboard analytics, user profiles, and bean pages.

    This operation:
    1. Filters reviews by optional user_id or bean_id
    2. Calculates total count and average rating
    3. Generates rating distribution (1-5 stars)
    4. Identifies top 10 most used tags
    5. Aggregates reviews by month (last 12 months)

    Args:
        user_id: Optional UUID to filter by specific user
        bean_id: Optional UUID to filter by specific bean

    Returns:
        Dictionary with statistics:
        - total_reviews: int - Total number of reviews
        - avg_rating: float - Average rating (rounded to 2 decimals)
        - rating_distribution: dict - Count for each rating (1-5)
        - top_tags: list - Top 10 tags with {id, name, count}
        - reviews_by_month: dict - Reviews count by month

    Example:
        >>> stats = get_review_statistics(user_id=user.id)
        >>> stats['total_reviews']
        42
        >>> stats['avg_rating']
        4.23
    """
    queryset = Review.objects.all()

    # Apply filters
    if user_id:
        queryset = queryset.filter(author_id=user_id)

    if bean_id:
        queryset = queryset.filter(coffeebean_id=bean_id)

    # Calculate basic statistics
    total_reviews = queryset.count()
    avg_rating = queryset.aggregate(avg=Avg('rating'))['avg'] or 0

    # Rating distribution (1-5 stars)
    rating_dist = {}
    for i in range(1, 6):
        rating_dist[str(i)] = queryset.filter(rating=i).count()

    # Top tags (most frequently used)
    # Uses filter on tags to avoid N+1 queries
    top_tags = list(
        Tag.objects.filter(reviews__in=queryset)
        .annotate(count=Count('reviews'))
        .order_by('-count')
        .values('id', 'name', 'count')[:10]
    )

    # Reviews by month (last 12 months)
    # TruncMonth groups by month, Count aggregates
    reviews_by_month = list(
        queryset
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('-month')[:12]
    )

    return {
        'total_reviews': total_reviews,
        'avg_rating': round(float(avg_rating), 2),
        'rating_distribution': rating_dist,
        'top_tags': top_tags,
        'reviews_by_month': {
            str(item['month'].date()): item['count']
            for item in reviews_by_month
        }
    }


def get_bean_review_summary(*, bean_id: UUID) -> dict:
    """
    Get comprehensive review summary for a specific coffee bean.

    Aggregates all review data for a bean to show overall rating,
    rating breakdown, and common flavor tags. Useful for bean detail
    pages and bean comparison features.

    This operation:
    1. Validates bean exists and is active
    2. Aggregates all reviews for the bean
    3. Calculates rating distribution
    4. Identifies top 10 most common tags

    Args:
        bean_id: UUID of coffee bean

    Returns:
        Dictionary with:
        - bean_id: str - UUID as string
        - bean_name: str - Formatted bean name
        - total_reviews: int - Total number of reviews
        - avg_rating: float - Average rating
        - rating_breakdown: dict - Count for each rating (1-5)
        - common_tags: list - Top 10 tags with {id, name, count}

    Raises:
        BeanNotFoundError: If bean doesn't exist or inactive

    Example:
        >>> summary = get_bean_review_summary(bean_id=bean.id)
        >>> summary['bean_name']
        'Counter Culture - Fast Forward'
        >>> summary['total_reviews']
        127
    """
    # Validate bean exists and is active
    try:
        bean = CoffeeBean.objects.get(id=bean_id, is_active=True)
    except CoffeeBean.DoesNotExist:
        raise BeanNotFoundError("Coffee bean not found or inactive")

    # Get all reviews for this bean
    reviews = Review.objects.filter(coffeebean=bean)

    # Rating breakdown (1-5 stars)
    rating_breakdown = {}
    for i in range(1, 6):
        rating_breakdown[str(i)] = reviews.filter(rating=i).count()

    # Common tags used in reviews for this bean
    # Efficient query with annotation
    common_tags = list(
        Tag.objects.filter(reviews__coffeebean=bean)
        .annotate(count=Count('reviews'))
        .order_by('-count')
        .values('id', 'name', 'count')[:10]
    )

    return {
        'bean_id': str(bean.id),
        'bean_name': f"{bean.roastery_name} - {bean.name}",
        'total_reviews': reviews.count(),
        'avg_rating': float(bean.avg_rating),
        'rating_breakdown': rating_breakdown,
        'common_tags': common_tags,
    }
