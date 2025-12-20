from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from datetime import datetime, timedelta
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from apps.accounts.models import User
from apps.groups.models import Group
from .analytics import AnalyticsQueries
from .serializers import (
    # Input serializers
    PeriodQuerySerializer,
    TopBeansQuerySerializer,
    TimeseriesQuerySerializer,
    # Response serializers
    UserConsumptionSerializer,
    GroupConsumptionSerializer,
    TopBeansResponseSerializer,
    TimeseriesResponseSerializer,
    TasteProfileSerializer,
    DashboardResponseSerializer,
    ErrorSerializer,
)
from .permissions import IsGroupMemberForAnalytics
from .exceptions import AnalyticsServiceError, InvalidMetricError


@extend_schema(
    parameters=[
        OpenApiParameter('period', OpenApiTypes.STR, description='Month period (YYYY-MM)'),
        OpenApiParameter('start_date', OpenApiTypes.DATE, description='Start date (YYYY-MM-DD)'),
        OpenApiParameter('end_date', OpenApiTypes.DATE, description='End date (YYYY-MM-DD)'),
    ],
    responses={
        200: UserConsumptionSerializer,
        400: ErrorSerializer,
    },
    description="Get user's coffee consumption statistics for a given period.",
    tags=['analytics'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_consumption(request, user_id=None):
    """Get user's coffee consumption statistics - thin HTTP handler."""
    # Use current user if no ID provided
    target_user_id = user_id if user_id is not None else request.user.id

    # Verify user exists
    get_object_or_404(User, id=target_user_id)

    # Validate query parameters using input serializer
    query_serializer = PeriodQuerySerializer(data=request.query_params)
    query_serializer.is_valid(raise_exception=True)
    params = query_serializer.validated_data

    # Get consumption data from service
    data = AnalyticsQueries.user_consumption(
        user_id=target_user_id,
        start_date=params.get('start_date'),
        end_date=params.get('end_date')
    )

    return Response(data)


@extend_schema(
    parameters=[
        OpenApiParameter('start_date', OpenApiTypes.DATE, description='Start date (YYYY-MM-DD)'),
        OpenApiParameter('end_date', OpenApiTypes.DATE, description='End date (YYYY-MM-DD)'),
    ],
    responses={
        200: GroupConsumptionSerializer,
        403: ErrorSerializer,
    },
    description="Get group's coffee consumption statistics with member breakdown.",
    tags=['analytics'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsGroupMemberForAnalytics])
def group_consumption(request, group_id):
    """Get group's coffee consumption statistics - thin HTTP handler."""
    # Verify group exists (permission already checked membership)
    get_object_or_404(Group, id=group_id)

    # Validate query parameters using input serializer
    query_serializer = PeriodQuerySerializer(data=request.query_params)
    query_serializer.is_valid(raise_exception=True)
    params = query_serializer.validated_data

    # Get consumption data from service (already returns plain dicts)
    data = AnalyticsQueries.group_consumption(
        group_id=group_id,
        start_date=params.get('start_date'),
        end_date=params.get('end_date')
    )

    return Response(data)


@extend_schema(
    parameters=[
        OpenApiParameter('metric', OpenApiTypes.STR, description="Ranking metric: 'rating', 'kg', 'money', 'reviews'", default='rating'),
        OpenApiParameter('period', OpenApiTypes.INT, description='Number of days to consider', default=30),
        OpenApiParameter('limit', OpenApiTypes.INT, description='Number of results', default=10),
    ],
    responses={
        200: TopBeansResponseSerializer,
        400: ErrorSerializer,
    },
    description="Get top-ranked coffee beans by various metrics (rating, kg purchased, money spent, review count).",
    tags=['analytics'],
)
@api_view(['GET'])
def top_beans(request):
    """Get top-ranked coffee beans by various metrics - thin HTTP handler."""
    # Validate query parameters using input serializer
    query_serializer = TopBeansQuerySerializer(data=request.query_params)
    query_serializer.is_valid(raise_exception=True)
    params = query_serializer.validated_data

    try:
        # Get top beans from service (already returns plain dicts)
        data = AnalyticsQueries.top_beans(
            metric=params.get('metric'),
            period_days=params.get('period'),
            limit=params.get('limit')
        )
    except InvalidMetricError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

    return Response({
        'metric': params.get('metric'),
        'period_days': params.get('period'),
        'results': data
    })


@extend_schema(
    parameters=[
        OpenApiParameter('user_id', OpenApiTypes.UUID, description='User ID (defaults to current user)'),
        OpenApiParameter('group_id', OpenApiTypes.UUID, description='Group ID for group consumption'),
        OpenApiParameter('granularity', OpenApiTypes.STR, description="Time granularity: 'day', 'week', 'month'", default='month'),
    ],
    responses={
        200: TimeseriesResponseSerializer,
        403: ErrorSerializer,
    },
    description="Get consumption data over time for charts. Can be filtered by user or group.",
    tags=['analytics'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsGroupMemberForAnalytics])
def consumption_timeseries(request):
    """Get consumption over time for charts - thin HTTP handler."""
    # Validate query parameters using input serializer
    query_serializer = TimeseriesQuerySerializer(data=request.query_params)
    query_serializer.is_valid(raise_exception=True)
    params = query_serializer.validated_data

    # Use current user if no user_id provided and no group_id
    user_id = params.get('user_id')
    group_id = params.get('group_id')

    if not user_id and not group_id:
        user_id = request.user.id

    # Get timeseries data from service (already returns plain dicts)
    data = AnalyticsQueries.consumption_timeseries(
        user_id=user_id if not group_id else None,
        group_id=group_id,
        granularity=params.get('granularity')
    )

    return Response({
        'granularity': params.get('granularity'),
        'data': data
    })


@extend_schema(
    responses={200: TasteProfileSerializer},
    description="Get user's taste profile based on their coffee reviews (favorite origins, roast profiles, tags).",
    tags=['analytics'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def taste_profile(request, user_id=None):
    """Get user's taste profile based on reviews - thin HTTP handler."""
    # Use current user if no ID provided
    target_user_id = user_id if user_id is not None else request.user.id

    # Verify user exists
    get_object_or_404(User, id=target_user_id)

    # Get taste profile from service (already returns plain dict)
    profile = AnalyticsQueries.user_taste_profile(target_user_id)

    if profile is None:
        return Response({
            'message': 'No reviews found for this user',
            'review_count': 0
        })

    return Response(profile)


@extend_schema(
    responses={200: DashboardResponseSerializer},
    description="Get dashboard summary for the current user including all data needed for the dashboard.",
    tags=['analytics'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    """Get comprehensive dashboard data for current user."""
    from apps.groups.models import Group, GroupMembership
    from apps.beans.models import CoffeeBean
    from apps.reviews.models import Review, UserLibraryEntry
    from apps.purchases.models import PaymentShare, PaymentStatus
    from apps.groups.serializers import GroupListSerializer

    user = request.user
    now = datetime.now()
    thirty_days_ago = (now - timedelta(days=30)).date()

    # Get user's groups
    groups = Group.objects.filter(
        memberships__user=user
    ).select_related('owner').prefetch_related('memberships').distinct()

    groups_data = GroupListSerializer(groups, many=True, context={'request': request}).data
    total_members = sum(g.get('member_count', 0) for g in groups_data)

    # Get user's library
    library_entries = UserLibraryEntry.objects.filter(user=user, is_archived=False)
    library_count = library_entries.count()
    library_recent = library_entries.filter(added_at__gte=thirty_days_ago).count()

    # Get user's reviews count
    reviews_count = Review.objects.filter(user=user).count()

    # Get total beans count
    beans_count = CoffeeBean.objects.filter(is_active=True).count()

    # Get outstanding payments
    outstanding_shares = PaymentShare.objects.filter(
        user=user,
        status=PaymentStatus.UNPAID
    ).select_related('purchase', 'purchase__coffeebean', 'purchase__group')

    outstanding_total = sum(share.amount_czk for share in outstanding_shares)
    outstanding_count = outstanding_shares.count()

    # Build outstanding payments data
    outstanding_payments = []
    for share in outstanding_shares[:5]:  # Limit to 5
        outstanding_payments.append({
            'id': str(share.id),
            'amount_czk': float(share.amount_czk),
            'bean_name': share.purchase.coffeebean.name if share.purchase.coffeebean else None,
            'group_name': share.purchase.group.name if share.purchase.group else None,
        })

    # Get consumption stats (optional, may be empty for new users)
    try:
        consumption = AnalyticsQueries.user_consumption(
            user_id=user.id,
            start_date=thirty_days_ago,
            end_date=now.date()
        )
    except Exception:
        consumption = None

    # Get taste profile (optional)
    try:
        taste_profile = AnalyticsQueries.user_taste_profile(user.id)
    except Exception:
        taste_profile = None

    return Response({
        # Quick stats
        'stats': {
            'reviews_count': reviews_count,
            'library_count': library_count,
            'groups_count': len(groups_data),
        },
        # Groups section
        'groups': {
            'list': groups_data,
            'total_members': total_members,
        },
        # Library section
        'library': {
            'count': library_count,
            'recent_count': library_recent,
        },
        # Beans catalog
        'beans': {
            'total_count': beans_count,
        },
        # Outstanding payments
        'payments': {
            'total_outstanding': float(outstanding_total),
            'count': outstanding_count,
            'list': outstanding_payments,
        },
        # Analytics (optional)
        'consumption': consumption,
        'taste_profile': taste_profile,
    })