from django.db.models import Sum, Count, Avg, F, Q, DecimalField
from django.db.models.functions import TruncMonth, Coalesce
from datetime import datetime, timedelta
from decimal import Decimal
from apps.purchases.models import PurchaseRecord, PaymentShare, PaymentStatus
from apps.reviews.models import Review
from apps.beans.models import CoffeeBean


class AnalyticsQueries:
    """Optimized SQL queries for analytics endpoints."""
    
    @staticmethod
    def user_consumption(user_id, start_date=None, end_date=None):
        """
        Calculate user's coffee consumption and spending.
        
        Returns:
            {
                'total_kg': Decimal,
                'total_spent_czk': Decimal,
                'purchases_count': int,
                'avg_price_per_kg': Decimal,
                'period_start': date,
                'period_end': date,
            }
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
        Calculate group's total consumption and per-member breakdown.
        
        Returns:
            {
                'total_kg': Decimal,
                'total_spent_czk': Decimal,
                'purchases_count': int,
                'member_breakdown': [
                    {
                        'user': User,
                        'total_kg': Decimal,
                        'total_spent_czk': Decimal,
                        'share_percentage': float,
                    }
                ],
            }
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
        
        Args:
            metric: 'rating', 'kg', 'money', 'reviews'
            period_days: Last N days (None for all time)
            limit: Number of results
        
        Returns:
            List of {bean, score, metadata}
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
        Get consumption over time (for charts).
        
        Args:
            user_id: User UUID (required if not group)
            group_id: Group UUID (required if not user)
            granularity: 'day', 'week', 'month'
        
        Returns:
            List of {period, kg, czk, purchases_count}
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
        Analyze user's taste preferences from reviews.
        
        Returns:
            {
                'favorite_tags': [{'tag': str, 'count': int}],
                'avg_rating': float,
                'preferred_roast': str,
                'preferred_origin': str,
                'review_count': int,
            }
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