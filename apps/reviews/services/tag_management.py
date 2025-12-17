"""Tag management service - Taste tags for coffee reviews."""

from django.db import transaction, IntegrityError
from django.db.models import QuerySet, Count
from uuid import UUID

from apps.reviews.models import Tag
from .exceptions import TagNotFoundError


@transaction.atomic
def create_tag(*, name: str, category: str = '') -> Tag:
    """
    Create a new taste tag.

    Tags are used to describe flavor profiles of coffee beans.
    Tag names must be unique.

    Args:
        name: Tag name (must be unique)
        category: Optional category for grouping tags (e.g., 'fruity', 'nutty')

    Returns:
        Created Tag instance

    Raises:
        IntegrityError: If tag with this name already exists
    """
    try:
        tag = Tag.objects.create(name=name, category=category)
    except IntegrityError:
        raise IntegrityError(f"Tag '{name}' already exists")

    return tag


def get_tag_by_id(*, tag_id: UUID) -> Tag:
    """
    Retrieve a tag by ID.

    Args:
        tag_id: UUID of tag

    Returns:
        Tag instance

    Raises:
        TagNotFoundError: If tag doesn't exist
    """
    try:
        tag = Tag.objects.get(id=tag_id)
    except Tag.DoesNotExist:
        raise TagNotFoundError("Tag not found")

    return tag


def get_popular_tags(*, limit: int = 20) -> QuerySet[Tag]:
    """
    Get most frequently used tags.

    Returns tags ordered by how many times they've been used in reviews.
    Useful for showing suggested tags to users or displaying tag clouds.

    Args:
        limit: Maximum number of tags to return (default: 20)

    Returns:
        QuerySet of Tag instances annotated with 'usage_count',
        ordered by usage count descending
    """
    return (
        Tag.objects
        .annotate(usage_count=Count('reviews'))
        .filter(usage_count__gt=0)  # Only tags actually used
        .order_by('-usage_count')[:limit]
    )


def search_tags(
    *,
    search: str = '',
    category: str = ''
) -> QuerySet[Tag]:
    """
    Search tags by name or category.

    Useful for autocomplete functionality when users are selecting tags.

    Args:
        search: Search term for tag name (case-insensitive)
        category: Filter by specific category

    Returns:
        QuerySet of matching Tag instances ordered by name
    """
    queryset = Tag.objects.all()

    if search:
        queryset = queryset.filter(name__icontains=search)

    if category:
        queryset = queryset.filter(category=category)

    return queryset.order_by('name')
