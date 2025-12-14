from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, serializers
from django.shortcuts import get_object_or_404
from datetime import datetime, timedelta
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from drf_spectacular.types import OpenApiTypes
from apps.accounts.models import User
from apps.groups.models import Group
from .analytics import AnalyticsQueries


# Response serializers for API documentation
class UserConsumptionSerializer(serializers.Serializer):
    total_kg = serializers.FloatField()
    total_czk = serializers.FloatField()
    purchases_count = serializers.IntegerField()
    unique_beans = serializers.IntegerField()
    avg_price_per_kg = serializers.FloatField(allow_null=True)


class MemberBreakdownUserSerializer(serializers.Serializer):
    id = serializers.CharField()
    email = serializers.EmailField()
    display_name = serializers.CharField()


class MemberBreakdownSerializer(serializers.Serializer):
    user = MemberBreakdownUserSerializer()
    kg = serializers.FloatField()
    czk = serializers.FloatField()


class GroupConsumptionSerializer(serializers.Serializer):
    total_kg = serializers.FloatField()
    total_czk = serializers.FloatField()
    purchases_count = serializers.IntegerField()
    unique_beans = serializers.IntegerField()
    member_breakdown = MemberBreakdownSerializer(many=True)


class TopBeanSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    roastery_name = serializers.CharField()
    score = serializers.FloatField()
    metric = serializers.CharField()
    review_count = serializers.IntegerField(required=False)
    avg_rating = serializers.FloatField(required=False)
    total_kg = serializers.FloatField(required=False)
    total_spent_czk = serializers.CharField(required=False)


class TopBeansResponseSerializer(serializers.Serializer):
    metric = serializers.CharField()
    period_days = serializers.IntegerField(allow_null=True)
    results = TopBeanSerializer(many=True)


class TimeseriesPointSerializer(serializers.Serializer):
    period = serializers.CharField()
    kg = serializers.FloatField()
    czk = serializers.FloatField()
    purchases_count = serializers.IntegerField()


class TimeseriesResponseSerializer(serializers.Serializer):
    granularity = serializers.CharField()
    data = TimeseriesPointSerializer(many=True)


class TasteProfileSerializer(serializers.Serializer):
    review_count = serializers.IntegerField()
    avg_rating = serializers.FloatField()
    favorite_origins = serializers.ListField(child=serializers.DictField())
    favorite_roast_profiles = serializers.ListField(child=serializers.DictField())
    common_tags = serializers.ListField(child=serializers.DictField())
    brew_methods = serializers.ListField(child=serializers.DictField())


class DashboardTopBeanSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    roastery_name = serializers.CharField()
    avg_rating = serializers.FloatField()
    review_count = serializers.IntegerField()


class DashboardResponseSerializer(serializers.Serializer):
    consumption = UserConsumptionSerializer()
    taste_profile = TasteProfileSerializer(allow_null=True)
    top_beans = DashboardTopBeanSerializer(many=True)


class ErrorSerializer(serializers.Serializer):
    error = serializers.CharField()


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
    """Get user's coffee consumption statistics."""
    # If no user_id, use current user
    if user_id is None:
        user_id = request.user.id
    
    # Verify user exists
    user = get_object_or_404(User, id=user_id)
    
    # Parse date range
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    period = request.query_params.get('period')
    
    if period:
        # Parse period like "2025-01"
        try:
            year, month = period.split('-')
            start_date = datetime(int(year), int(month), 1).date()
            # Last day of month
            if int(month) == 12:
                end_date = datetime(int(year) + 1, 1, 1).date() - timedelta(days=1)
            else:
                end_date = datetime(int(year), int(month) + 1, 1).date() - timedelta(days=1)
        except (ValueError, AttributeError):
            return Response(
                {'error': 'Invalid period format. Use YYYY-MM'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Get consumption data
    data = AnalyticsQueries.user_consumption(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date
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
@permission_classes([IsAuthenticated])
def group_consumption(request, group_id):
    """Get group's coffee consumption statistics."""
    # Verify user is member of group
    group = get_object_or_404(Group, id=group_id)
    
    if not group.has_member(request.user):
        return Response(
            {'error': 'You must be a member of this group'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Parse date range
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    
    # Get consumption data
    data = AnalyticsQueries.group_consumption(
        group_id=group_id,
        start_date=start_date,
        end_date=end_date
    )

    # Serialize User objects in member_breakdown
    if 'member_breakdown' in data:
        for member in data['member_breakdown']:
            if 'user' in member:
                user = member['user']
                member['user'] = {
                    'id': str(user.id),
                    'email': user.email,
                    'display_name': user.get_display_name(),
                }

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
    """Get top-ranked coffee beans by various metrics."""
    metric = request.query_params.get('metric', 'rating')
    period_days = request.query_params.get('period', 30)
    limit = request.query_params.get('limit', 10)
    
    try:
        period_days = int(period_days) if period_days else None
        limit = int(limit)
    except ValueError:
        return Response(
            {'error': 'Invalid period or limit'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get top beans
    data = AnalyticsQueries.top_beans(
        metric=metric,
        period_days=period_days,
        limit=limit
    )
    
    # Format response
    results = []
    for item in data:
        bean_data = {
            'id': str(item['bean'].id),
            'name': item['bean'].name,
            'roastery_name': item['bean'].roastery_name,
            'score': item['score'],
            'metric': item.get('metric', metric),
        }
        
        # Add metric-specific data
        if 'review_count' in item:
            bean_data['review_count'] = item['review_count']
        if 'avg_rating' in item:
            bean_data['avg_rating'] = item['avg_rating']
        if 'total_kg' in item:
            bean_data['total_kg'] = item['total_kg']
        if 'total_spent_czk' in item:
            bean_data['total_spent_czk'] = str(item['total_spent_czk'])
        
        results.append(bean_data)
    
    return Response({
        'metric': metric,
        'period_days': period_days,
        'results': results
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
@permission_classes([IsAuthenticated])
def consumption_timeseries(request):
    """Get consumption over time for charts."""
    user_id = request.query_params.get('user_id', request.user.id)
    group_id = request.query_params.get('group_id')
    granularity = request.query_params.get('granularity', 'month')
    
    if group_id:
        # Verify membership
        group = get_object_or_404(Group, id=group_id)
        if not group.has_member(request.user):
            return Response(
                {'error': 'You must be a member of this group'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    # Get timeseries data
    data = AnalyticsQueries.consumption_timeseries(
        user_id=user_id if not group_id else None,
        group_id=group_id,
        granularity=granularity
    )
    
    # Format response
    formatted_data = []
    for item in data:
        formatted_data.append({
            'period': item['period'],
            'kg': float(item['kg']),
            'czk': float(item['czk']),
            'purchases_count': item['purchases_count']
        })
    
    return Response({
        'granularity': granularity,
        'data': formatted_data
    })


@extend_schema(
    responses={200: TasteProfileSerializer},
    description="Get user's taste profile based on their coffee reviews (favorite origins, roast profiles, tags).",
    tags=['analytics'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def taste_profile(request, user_id=None):
    """Get user's taste profile based on reviews."""
    # If no user_id, use current user
    if user_id is None:
        user_id = request.user.id
    
    # Get taste profile
    profile = AnalyticsQueries.user_taste_profile(user_id)
    
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
    """Get dashboard summary for current user."""
    user = request.user
    
    # Get user consumption (last 30 days)
    consumption = AnalyticsQueries.user_consumption(
        user_id=user.id,
        start_date=(datetime.now() - timedelta(days=30)).date(),
        end_date=datetime.now().date()
    )
    
    # Get taste profile
    taste_profile = AnalyticsQueries.user_taste_profile(user.id)
    
    # Get top beans
    top_beans = AnalyticsQueries.top_beans(metric='rating', period_days=30, limit=5)
    
    return Response({
        'consumption': consumption,
        'taste_profile': taste_profile,
        'top_beans': [
            {
                'id': str(item['bean'].id),
                'name': item['bean'].name,
                'roastery_name': item['bean'].roastery_name,
                'avg_rating': item.get('avg_rating', item['score']),
                'review_count': item.get('review_count', 0),
            }
            for item in top_beans
        ]
    })