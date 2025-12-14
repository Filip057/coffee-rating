from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from datetime import datetime, timedelta
from apps.accounts.models import User
from apps.groups.models import Group
from .analytics import AnalyticsQueries


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_consumption(request, user_id=None):
    """
    Get user's coffee consumption statistics.
    
    GET /api/analytics/user/{user_id}/consumption/
    Query params:
    - period: YYYY-MM (e.g., 2025-01) or date range
    - start_date: YYYY-MM-DD
    - end_date: YYYY-MM-DD
    """
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def group_consumption(request, group_id):
    """
    Get group's coffee consumption statistics.
    
    GET /api/analytics/group/{group_id}/consumption/
    Query params:
    - start_date: YYYY-MM-DD
    - end_date: YYYY-MM-DD
    """
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


@api_view(['GET'])
def top_beans(request):
    """
    Get top-ranked coffee beans by various metrics.
    
    GET /api/analytics/beans/top/
    Query params:
    - metric: 'rating', 'kg', 'money', 'reviews' (default: rating)
    - period: number of days (default: 30)
    - limit: number of results (default: 10)
    """
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def consumption_timeseries(request):
    """
    Get consumption over time for charts.
    
    GET /api/analytics/timeseries/
    Query params:
    - user_id: UUID (optional, defaults to current user)
    - group_id: UUID (optional)
    - granularity: 'day', 'week', 'month' (default: month)
    """
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def taste_profile(request, user_id=None):
    """
    Get user's taste profile based on reviews.
    
    GET /api/analytics/user/{user_id}/taste-profile/
    """
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    """
    Get dashboard summary for current user.
    
    GET /api/analytics/dashboard/
    """
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