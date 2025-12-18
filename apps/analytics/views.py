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
    description="Get dashboard summary for the current user including consumption, taste profile, and top beans.",
    tags=['analytics'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    """Get dashboard summary for current user - thin HTTP handler."""
    user = request.user

    # Get user consumption (last 30 days) from service
    consumption = AnalyticsQueries.user_consumption(
        user_id=user.id,
        start_date=(datetime.now() - timedelta(days=30)).date(),
        end_date=datetime.now().date()
    )

    # Get taste profile from service
    taste_profile = AnalyticsQueries.user_taste_profile(user.id)

    # Get top beans from service (already returns plain dicts)
    top_beans_data = AnalyticsQueries.top_beans(
        metric='rating',
        period_days=30,
        limit=5
    )

    return Response({
        'consumption': consumption,
        'taste_profile': taste_profile,
        'top_beans': top_beans_data
    })