"""Bean search and filtering service."""

from django.db.models import Q, QuerySet
from typing import Optional

from ..models import CoffeeBean


def search_beans(
    *,
    search: Optional[str] = None,
    roastery: Optional[str] = None,
    origin: Optional[str] = None,
    roast_profile: Optional[str] = None,
    processing: Optional[str] = None,
    min_rating: Optional[float] = None,
    only_active: bool = True
) -> QuerySet[CoffeeBean]:
    """
    Search and filter coffee beans.

    Args:
        search: Search term for name, roastery, origin, description
        roastery: Filter by roastery name
        origin: Filter by origin country
        roast_profile: Filter by roast profile
        processing: Filter by processing method
        min_rating: Minimum average rating
        only_active: Only return active beans

    Returns:
        Filtered QuerySet of CoffeeBean
    """
    queryset = CoffeeBean.objects.select_related('created_by').prefetch_related('variants')

    if only_active:
        queryset = queryset.filter(is_active=True)

    # Search across multiple fields
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(roastery_name__icontains=search) |
            Q(origin_country__icontains=search) |
            Q(description__icontains=search) |
            Q(tasting_notes__icontains=search)
        )

    # Specific filters
    if roastery:
        queryset = queryset.filter(roastery_name__icontains=roastery)

    if origin:
        queryset = queryset.filter(origin_country__icontains=origin)

    if roast_profile:
        queryset = queryset.filter(roast_profile=roast_profile)

    if processing:
        queryset = queryset.filter(processing=processing)

    if min_rating is not None:
        queryset = queryset.filter(avg_rating__gte=min_rating)

    return queryset.distinct()


def get_all_roasteries(*, only_active: bool = True) -> list[str]:
    """
    Get list of all unique roastery names.

    Args:
        only_active: Only include active beans

    Returns:
        Sorted list of roastery names
    """
    queryset = CoffeeBean.objects.all()

    if only_active:
        queryset = queryset.filter(is_active=True)

    roasteries = (
        queryset
        .values_list('roastery_name', flat=True)
        .distinct()
        .order_by('roastery_name')
    )

    return list(roasteries)


def get_all_origins(*, only_active: bool = True) -> list[str]:
    """
    Get list of all unique origin countries.

    Args:
        only_active: Only include active beans

    Returns:
        Sorted list of origin countries
    """
    queryset = CoffeeBean.objects.all()

    if only_active:
        queryset = queryset.filter(is_active=True)

    origins = (
        queryset
        .filter(origin_country__isnull=False)
        .exclude(origin_country='')
        .values_list('origin_country', flat=True)
        .distinct()
        .order_by('origin_country')
    )

    return list(origins)
