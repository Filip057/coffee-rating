"""
Analytics Module
=================

This module provides optimized query methods for analytics and statistics.
It aggregates data from purchases, reviews, and beans to power dashboards,
charts, and insights.

Classes:
    AnalyticsQueries: Static methods for various analytics queries.

Key Features:
    - User consumption tracking (kg, spending)
    - Group consumption with member breakdown
    - Top beans rankings by various metrics
    - Consumption timeseries for charts
    - User taste profile analysis

Example:
    Getting user statistics::

        from apps.analytics.analytics import AnalyticsQueries

        # Get user's consumption for last 30 days
        stats = AnalyticsQueries.user_consumption(
            user_id=user.id,
            start_date=date.today() - timedelta(days=30),
            end_date=date.today(),
        )
        print(f"You consumed {stats['total_kg']} kg")
        print(f"Total spent: {stats['total_spent_czk']} CZK")

Note:
    This module is read-only and doesn't modify any data. All methods
    are static and can be called without instantiation.
"""

from django.db.models import Sum, Count, Avg, F, Q, DecimalField
from django.db.models.functions import TruncMonth, Coalesce
from datetime import datetime, timedelta
from decimal import Decimal
from apps.purchases.models import PurchaseRecord, PaymentShare, PaymentStatus
from apps.reviews.models import Review
from apps.beans.models import CoffeeBean


class AnalyticsQueries:
    """
    Optimized SQL queries for analytics endpoints.

    This class provides static methods for calculating various analytics
    and statistics from purchases, reviews, and beans data. All methods
    are optimized to minimize database queries.

    Methods:
        user_consumption: Calculate user's coffee consumption and spending.
        group_consumption: Calculate group consumption with member breakdown.
        top_beans: Get top-ranked beans by various metrics.
        consumption_timeseries: Get consumption over time for charts.
        user_taste_profile: Analyze user's taste preferences from reviews.

    Example:
        Dashboard data aggregation::

            consumption = AnalyticsQueries.user_consumption(user.id)
            taste = AnalyticsQueries.user_taste_profile(user.id)
            top = AnalyticsQueries.top_beans(metric='rating', limit=5)

    Note:
        All methods return plain dictionaries or lists, not Django objects,
        making them suitable for JSON serialization in API responses.
    """
    
    @staticmethod
    def user_consumption(user_id, start_date=None, end_date=None):
        """
        Calculate a user's coffee consumption and spending statistics.

        This method aggregates data from the user's paid PaymentShares to
        calculate total weight consumed and money spent. Weight is calculated
        proportionally based on payment share ratios.

        Args:
            user_id (UUID): The user's unique identifier.
            start_date (date, optional): Start of period to analyze.
                If None, includes all historical data.
            end_date (date, optional): End of period to analyze.
                If None, includes up to current date.

        Returns:
            dict: A dictionary containing:
                - total_kg (Decimal): Total coffee consumed in kilograms.
                - total_spent_czk (Decimal): Total amount spent in CZK.
                - purchases_count (int): Number of purchases included.
                - avg_price_per_kg (Decimal): Average price per kilogram.
                - period_start (date | None): The start_date parameter.
                - period_end (date | None): The end_date parameter.

        Example:
            Get all-time consumption::

                stats = AnalyticsQueries.user_consumption(user.id)
                print(f"Total: {stats['total_kg']} kg for {stats['total_spent_czk']} CZK")

            Get monthly consumption::

                stats = AnalyticsQueries.user_consumption(
                    user.id,
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 1, 31),
                )

        Note:
            Weight calculation formula:
            ``user_weight = (user_payment / total_price) * package_weight``

            This ensures that in group purchases, each member's weight share
            is proportional to their payment share.
        """
        # Base queryset: user's payment shares that are paid
        shares = PaymentShare.objects.filter(
            user_id=user_id,
            status=PaymentStatus.PAID
        ).select_related('purchase')
        
        # Date filtering
        if start_date:
            shares = shares.filter(purchase__date__gte=start_date)
        if end_date:
            shares = shares.filter(purchase__date__lte=end_date)
        
        # Aggregate spending
        spending = shares.aggregate(
            total=Coalesce(Sum('amount_czk'), Decimal('0.00'))
        )['total']
        
        # Calculate weight consumed
        # For each purchase, user's share = (user_payment / total_price) * package_weight
        total_grams = Decimal('0.00')
        purchase_count = 0
        
        for share in shares.select_related('purchase'):
            purchase = share.purchase
            if purchase.package_weight_grams:
                # Calculate user's weight share
                share_ratio = share.amount_czk / purchase.total_price_czk
                user_grams = Decimal(purchase.package_weight_grams) * share_ratio
                total_grams += user_grams
                purchase_count += 1
        
        total_kg = total_grams / Decimal('1000.0')
        avg_price_per_kg = (spending / total_kg) if total_kg > 0 else Decimal('0.00')
        
        return {
            'total_kg': round(total_kg, 3),
            'total_spent_czk': spending,
            'purchases_count': purchase_count,
            'avg_price_per_kg': round(avg_price_per_kg, 2),
            'period_start': start_date,
            'period_end': end_date,
        }
    
    @staticmethod
    def group_consumption(group_id, start_date=None, end_date=None):
        """
        Calculate a group's total consumption and per-member breakdown.

        This method provides a comprehensive view of a group's coffee
        consumption, including totals and individual member contributions.

        Args:
            group_id (UUID): The group's unique identifier.
            start_date (date, optional): Start of period to analyze.
            end_date (date, optional): End of period to analyze.

        Returns:
            dict: A dictionary containing:
                - total_kg (Decimal): Total coffee consumed by the group.
                - total_spent_czk (Decimal): Total spent by the group.
                - purchases_count (int): Number of group purchases.
                - member_breakdown (list[dict]): Per-member statistics, each containing:
                    - user (User): The user object.
                    - total_kg (Decimal): User's portion of consumption.
                    - total_spent_czk (Decimal): User's total spending.
                    - share_percentage (float): User's share as percentage of total.

        Example:
            Get group statistics::

                stats = AnalyticsQueries.group_consumption(group.id)
                print(f"Group total: {stats['total_kg']} kg")
                for member in stats['member_breakdown']:
                    print(f"  {member['user'].email}: {member['share_percentage']}%")

        Note:
            The member_breakdown includes all current group members, even if
            they haven't participated in any purchases (they'll have 0 values).
            This is useful for showing contribution imbalances.
        """
        # Get group purchases
        purchases = PurchaseRecord.objects.filter(group_id=group_id)
        
        if start_date:
            purchases = purchases.filter(date__gte=start_date)
        if end_date:
            purchases = purchases.filter(date__lte=end_date)
        
        # Group totals
        totals = purchases.aggregate(
            total_czk=Coalesce(Sum('total_price_czk'), Decimal('0.00')),
            total_grams=Coalesce(
                Sum('package_weight_grams'),
                0
            ),
            count=Count('id')
        )
        
        total_kg = Decimal(totals['total_grams']) / Decimal('1000.0')
        
        # Per-member breakdown
        from apps.groups.models import GroupMembership
        memberships = GroupMembership.objects.filter(
            group_id=group_id
        ).select_related('user')
        
        member_breakdown = []
        for membership in memberships:
            user_data = AnalyticsQueries.user_consumption(
                membership.user_id,
                start_date,
                end_date
            )
            
            share_pct = 0.0
            if totals['total_czk'] > 0:
                share_pct = float(
                    (user_data['total_spent_czk'] / totals['total_czk']) * 100
                )
            
            member_breakdown.append({
                'user': membership.user,
                'total_kg': user_data['total_kg'],
                'total_spent_czk': user_data['total_spent_czk'],
                'share_percentage': round(share_pct, 2),
            })
        
        return {
            'total_kg': round(total_kg, 3),
            'total_spent_czk': totals['total_czk'],
            'purchases_count': totals['count'],
            'member_breakdown': member_breakdown,
        }
    
    @staticmethod
    def top_beans(metric='rating', period_days=30, limit=10):
        """
        Get top-ranked coffee beans by various metrics.

        This method provides flexible bean rankings that can be used for
        leaderboards, recommendations, and trending beans features.

        Args:
            metric (str, optional): The ranking metric. Options:
                - 'rating': Average review rating (requires min 3 reviews).
                - 'kg': Total kilograms purchased.
                - 'money': Total CZK spent on purchases.
                - 'reviews': Total number of reviews.
                Defaults to 'rating'.
            period_days (int | None, optional): Limit to last N days.
                If None, includes all-time data.
                Defaults to 30.
            limit (int, optional): Maximum number of results to return.
                Defaults to 10.

        Returns:
            list[dict]: List of dictionaries, each containing:
                - bean (CoffeeBean): The coffee bean object.
                - score (float): The ranking score (varies by metric).
                - metric (str): Human-readable metric name.
                - Additional metric-specific fields (review_count, avg_rating,
                  total_kg, total_spent_czk).

        Raises:
            ValueError: If an invalid metric is specified.

        Example:
            Top beans by rating::

                top_rated = AnalyticsQueries.top_beans(metric='rating', limit=5)
                for item in top_rated:
                    print(f"{item['bean'].name}: {item['score']} stars")

            Most purchased beans this month::

                top_kg = AnalyticsQueries.top_beans(metric='kg', period_days=30)
                for item in top_kg:
                    print(f"{item['bean'].name}: {item['total_kg']} kg")

        Note:
            For 'rating' metric, beans must have at least 3 reviews to be
            included. This prevents single 5-star reviews from dominating
            the leaderboard.
        """
        cutoff_date = None
        if period_days:
            cutoff_date = datetime.now().date() - timedelta(days=period_days)
        
        if metric == 'rating':
            # Top by average rating (min 3 reviews)
            beans = CoffeeBean.objects.filter(
                review_count__gte=3,
                is_active=True
            ).order_by('-avg_rating', '-review_count')[:limit]
            
            return [
                {
                    'bean': bean,
                    'score': float(bean.avg_rating),
                    'review_count': bean.review_count,
                    'metric': 'Average Rating'
                }
                for bean in beans
            ]
        
        elif metric == 'kg':
            # Top by total weight purchased
            purchases = PurchaseRecord.objects.filter(
                coffeebean__isnull=False
            )
            if cutoff_date:
                purchases = purchases.filter(date__gte=cutoff_date)
            
            top_beans = purchases.values(
                'coffeebean_id',
                'coffeebean__name',
                'coffeebean__roastery_name'
            ).annotate(
                total_grams=Sum('package_weight_grams')
            ).order_by('-total_grams')[:limit]
            
            results = []
            for item in top_beans:
                bean = CoffeeBean.objects.get(id=item['coffeebean_id'])
                total_kg = Decimal(item['total_grams'] or 0) / Decimal('1000.0')
                results.append({
                    'bean': bean,
                    'score': float(total_kg),
                    'total_kg': round(total_kg, 3),
                    'metric': 'Total Kilograms'
                })
            
            return results
        
        elif metric == 'money':
            # Top by total money spent
            purchases = PurchaseRecord.objects.filter(
                coffeebean__isnull=False
            )
            if cutoff_date:
                purchases = purchases.filter(date__gte=cutoff_date)
            
            top_beans = purchases.values(
                'coffeebean_id'
            ).annotate(
                total_czk=Sum('total_price_czk')
            ).order_by('-total_czk')[:limit]
            
            results = []
            for item in top_beans:
                bean = CoffeeBean.objects.get(id=item['coffeebean_id'])
                results.append({
                    'bean': bean,
                    'score': float(item['total_czk']),
                    'total_spent_czk': item['total_czk'],
                    'metric': 'Total Spent (CZK)'
                })
            
            return results
        
        elif metric == 'reviews':
            # Top by review count
            beans = CoffeeBean.objects.filter(
                review_count__gt=0,
                is_active=True
            ).order_by('-review_count', '-avg_rating')[:limit]
            
            return [
                {
                    'bean': bean,
                    'score': bean.review_count,
                    'review_count': bean.review_count,
                    'avg_rating': float(bean.avg_rating),
                    'metric': 'Number of Reviews'
                }
                for bean in beans
            ]
        
        else:
            raise ValueError(f"Invalid metric: {metric}")
    
    @staticmethod
    def consumption_timeseries(user_id=None, group_id=None, granularity='month'):
        """
        Get consumption data over time for chart visualizations.

        This method generates time-series data suitable for line charts,
        bar charts, or other temporal visualizations of consumption patterns.

        Args:
            user_id (UUID, optional): The user's unique identifier.
                Required if group_id is not provided.
            group_id (UUID, optional): The group's unique identifier.
                Required if user_id is not provided.
            granularity (str, optional): Time period grouping.
                Currently only 'month' is implemented.
                Defaults to 'month'.

        Returns:
            list[dict]: List of dictionaries, each containing:
                - period (str): Period label (e.g., '2025-01' for months).
                - kg (Decimal): Coffee consumed in this period.
                - czk (Decimal): Amount spent in this period.
                - purchases_count (int): Number of purchases in this period.

        Raises:
            ValueError: If neither user_id nor group_id is provided.

        Example:
            User's monthly consumption::

                data = AnalyticsQueries.consumption_timeseries(user_id=user.id)
                for point in data:
                    print(f"{point['period']}: {point['kg']} kg, {point['czk']} CZK")
                # Output:
                # 2025-01: 0.5 kg, 450.00 CZK
                # 2025-02: 0.75 kg, 650.00 CZK

            Group's monthly consumption::

                data = AnalyticsQueries.consumption_timeseries(group_id=group.id)

        Note:
            For user timeseries, only PAID payment shares are included.
            For group timeseries, all purchases are included regardless
            of payment status.
        """
        if user_id:
            # User's paid shares
            shares = PaymentShare.objects.filter(
                user_id=user_id,
                status=PaymentStatus.PAID
            ).select_related('purchase')
            
            # Group by month
            series = []
            shares_by_month = {}
            
            for share in shares:
                month_key = share.purchase.date.strftime('%Y-%m')
                if month_key not in shares_by_month:
                    shares_by_month[month_key] = {
                        'czk': Decimal('0.00'),
                        'grams': Decimal('0.00'),
                        'count': 0
                    }
                
                shares_by_month[month_key]['czk'] += share.amount_czk
                
                # Calculate weight share
                if share.purchase.package_weight_grams:
                    share_ratio = share.amount_czk / share.purchase.total_price_czk
                    grams = Decimal(share.purchase.package_weight_grams) * share_ratio
                    shares_by_month[month_key]['grams'] += grams
                
                shares_by_month[month_key]['count'] += 1
            
            # Convert to list
            for month, data in sorted(shares_by_month.items()):
                series.append({
                    'period': month,
                    'kg': round(data['grams'] / Decimal('1000.0'), 3),
                    'czk': data['czk'],
                    'purchases_count': data['count']
                })
            
            return series
        
        elif group_id:
            # Group purchases
            purchases = PurchaseRecord.objects.filter(
                group_id=group_id
            ).order_by('date')
            
            series = []
            purchases_by_month = {}
            
            for purchase in purchases:
                month_key = purchase.date.strftime('%Y-%m')
                if month_key not in purchases_by_month:
                    purchases_by_month[month_key] = {
                        'czk': Decimal('0.00'),
                        'grams': 0,
                        'count': 0
                    }
                
                purchases_by_month[month_key]['czk'] += purchase.total_price_czk
                purchases_by_month[month_key]['grams'] += purchase.package_weight_grams or 0
                purchases_by_month[month_key]['count'] += 1
            
            for month, data in sorted(purchases_by_month.items()):
                series.append({
                    'period': month,
                    'kg': round(Decimal(data['grams']) / Decimal('1000.0'), 3),
                    'czk': data['czk'],
                    'purchases_count': data['count']
                })
            
            return series
        
        else:
            raise ValueError("Either user_id or group_id required")
    
    @staticmethod
    def user_taste_profile(user_id):
        """
        Analyze a user's taste preferences based on their reviews.

        This method aggregates data from all of a user's reviews to build
        a profile of their taste preferences, including favorite flavors,
        preferred roast levels, and favorite origins.

        Args:
            user_id (UUID): The user's unique identifier.

        Returns:
            dict | None: A dictionary containing taste preferences, or None
            if the user has no reviews. Dictionary contains:
                - favorite_tags (list[dict]): Top 10 taste tags, each with:
                    - tag (str): Tag name.
                    - count (int): Number of times used in reviews.
                - avg_rating (float): User's average rating across all reviews.
                - preferred_roast (str | None): Most common roast profile in
                  reviewed beans.
                - preferred_origin (str | None): Most common origin country in
                  reviewed beans.
                - review_count (int): Total number of reviews by this user.

        Example:
            Get user preferences::

                profile = AnalyticsQueries.user_taste_profile(user.id)
                if profile:
                    print(f"Reviews: {profile['review_count']}")
                    print(f"Average rating: {profile['avg_rating']}")
                    print(f"Favorite roast: {profile['preferred_roast']}")
                    print(f"Favorite origin: {profile['preferred_origin']}")
                    print("Top flavor tags:")
                    for tag in profile['favorite_tags'][:5]:
                        print(f"  - {tag['tag']}: {tag['count']} times")
                else:
                    print("No reviews yet")

        Note:
            Returns None (not an empty dict) if the user has no reviews.
            This allows the caller to easily distinguish between "no data"
            and "data with zero values".
        """
        from apps.reviews.models import Tag
        
        reviews = Review.objects.filter(
            author_id=user_id
        ).select_related('coffeebean').prefetch_related('taste_tags')
        
        if not reviews.exists():
            return None
        
        # Aggregate data
        total_rating = 0
        tag_counts = {}
        roast_counts = {}
        origin_counts = {}
        
        for review in reviews:
            total_rating += review.rating
            
            # Count tags
            for tag in review.taste_tags.all():
                tag_counts[tag.name] = tag_counts.get(tag.name, 0) + 1
            
            # Count roast profiles
            roast = review.coffeebean.roast_profile
            roast_counts[roast] = roast_counts.get(roast, 0) + 1
            
            # Count origins
            origin = review.coffeebean.origin_country
            if origin:
                origin_counts[origin] = origin_counts.get(origin, 0) + 1
        
        review_count = reviews.count()
        
        # Sort and format
        favorite_tags = [
            {'tag': tag, 'count': count}
            for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        preferred_roast = max(roast_counts.items(), key=lambda x: x[1])[0] if roast_counts else None
        preferred_origin = max(origin_counts.items(), key=lambda x: x[1])[0] if origin_counts else None
        
        return {
            'favorite_tags': favorite_tags,
            'avg_rating': round(total_rating / review_count, 2),
            'preferred_roast': preferred_roast,
            'preferred_origin': preferred_origin,
            'review_count': review_count,
        }