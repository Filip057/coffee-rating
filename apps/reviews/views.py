from rest_framework import status, generics, viewsets
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db import transaction
from django.db.models import Count, Avg, Q
from django.shortcuts import get_object_or_404
from .models import Review, Tag, UserLibraryEntry
from .serializers import (
    ReviewSerializer,
    ReviewCreateSerializer,
    TagSerializer,
    UserLibraryEntrySerializer,
    ReviewStatisticsSerializer,
    BeanReviewSummarySerializer,
)
from apps.beans.models import CoffeeBean
from apps.groups.models import Group
from .permissions import IsReviewAuthorOrReadOnly


class ReviewPagination(PageNumberPagination):
    """Custom pagination for reviews."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Review CRUD operations.
    
    list: Get all reviews (with filters)
    create: Create a new review (auto-creates library entry)
    retrieve: Get a specific review
    update: Update a review (author only)
    partial_update: Partially update a review (author only)
    destroy: Delete a review (author only)
    """
    
    queryset = Review.objects.select_related(
        'author',
        'coffeebean',
        'group'
    ).prefetch_related('taste_tags')
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsReviewAuthorOrReadOnly]
    pagination_class = ReviewPagination
    
    def get_queryset(self):
        """
        Filter reviews based on query parameters.
        
        Filters:
        - coffeebean: UUID of coffee bean
        - author: UUID of author
        - group: UUID of group
        - rating: Exact rating (1-5)
        - min_rating: Minimum rating
        - context: personal/group/public
        - search: Search in notes
        """
        queryset = super().get_queryset()
        
        # Filter by coffee bean
        coffeebean_id = self.request.query_params.get('coffeebean')
        if coffeebean_id:
            queryset = queryset.filter(coffeebean_id=coffeebean_id)
        
        # Filter by author
        author_id = self.request.query_params.get('author')
        if author_id:
            queryset = queryset.filter(author_id=author_id)
        
        # Filter by group
        group_id = self.request.query_params.get('group')
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        
        # Filter by rating
        rating = self.request.query_params.get('rating')
        if rating:
            queryset = queryset.filter(rating=rating)
        
        min_rating = self.request.query_params.get('min_rating')
        if min_rating:
            queryset = queryset.filter(rating__gte=min_rating)
        
        # Filter by context
        context = self.request.query_params.get('context')
        if context:
            queryset = queryset.filter(context=context)
        
        # Search in notes
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(notes__icontains=search) | 
                Q(coffeebean__name__icontains=search) |
                Q(coffeebean__roastery_name__icontains=search)
            )
        
        # Filter by tag
        tag_id = self.request.query_params.get('tag')
        if tag_id:
            queryset = queryset.filter(taste_tags__id=tag_id)
        
        return queryset.distinct()
    
    def get_serializer_class(self):
        """Use different serializer for creation."""
        if self.action == 'create':
            return ReviewCreateSerializer
        return ReviewSerializer
    
    @transaction.atomic
    def perform_create(self, serializer):
        """
        Create review with transaction safety.
        
        Steps:
        1. Create review with author
        2. Auto-create UserLibraryEntry
        3. Update bean's aggregate rating
        """
        # Create review
        review = serializer.save(author=self.request.user)
        
        # Auto-create library entry
        UserLibraryEntry.ensure_entry(
            user=self.request.user,
            coffeebean=review.coffeebean,
            added_by='review'
        )
        
        # Update aggregate rating (done outside transaction via signal)
        transaction.on_commit(lambda: review.coffeebean.update_aggregate_rating())
    
    @transaction.atomic
    def perform_update(self, serializer):
        """Update review and recalculate aggregate."""
        review = serializer.save()
        transaction.on_commit(lambda: review.coffeebean.update_aggregate_rating())
    
    @transaction.atomic
    def perform_destroy(self, instance):
        """Delete review and recalculate aggregate."""
        coffeebean = instance.coffeebean
        instance.delete()
        transaction.on_commit(lambda: coffeebean.update_aggregate_rating())
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_reviews(self, request):
        """Get current user's reviews."""
        reviews = self.get_queryset().filter(author=request.user)
        page = self.paginate_queryset(reviews)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get review statistics.
        
        Returns:
        - Total reviews
        - Average rating
        - Rating distribution
        - Top tags
        - Reviews by month
        """
        queryset = self.get_queryset()
        
        # Filter by user or bean if specified
        user_id = request.query_params.get('user_id')
        bean_id = request.query_params.get('bean_id')
        
        if user_id:
            queryset = queryset.filter(author_id=user_id)
        if bean_id:
            queryset = queryset.filter(coffeebean_id=bean_id)
        
        # Calculate statistics
        total_reviews = queryset.count()
        avg_rating = queryset.aggregate(avg=Avg('rating'))['avg'] or 0
        
        # Rating distribution
        rating_dist = {}
        for i in range(1, 6):
            rating_dist[str(i)] = queryset.filter(rating=i).count()
        
        # Top tags
        top_tags = list(
            Tag.objects.filter(reviews__in=queryset)
            .annotate(count=Count('reviews'))
            .order_by('-count')
            .values('id', 'name', 'count')[:10]
        )
        
        # Reviews by month (last 12 months)
        from django.db.models.functions import TruncMonth
        reviews_by_month = list(
            queryset
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('-month')[:12]
        )
        
        data = {
            'total_reviews': total_reviews,
            'avg_rating': round(float(avg_rating), 2),
            'rating_distribution': rating_dist,
            'top_tags': top_tags,
            'reviews_by_month': {
                str(item['month'].date()): item['count']
                for item in reviews_by_month
            }
        }
        
        serializer = ReviewStatisticsSerializer(data)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_library(request):
    """
    Get user's coffee library.
    
    GET /api/reviews/library/
    Query params:
    - archived: true/false (default: false)
    - search: Search in bean name
    """
    archived = request.GET.get('archived', 'false').lower() == 'true'
    search = request.GET.get('search')
    
    library = UserLibraryEntry.objects.filter(
        user=request.user,
        is_archived=archived
    ).select_related('coffeebean')
    
    if search:
        library = library.filter(
            Q(coffeebean__name__icontains=search) |
            Q(coffeebean__roastery_name__icontains=search)
        )
    
    library = library.order_by('-added_at')
    
    serializer = UserLibraryEntrySerializer(library, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_library(request):
    """
    Manually add coffee bean to user's library.
    
    POST /api/reviews/library/add/
    Body: {"coffeebean_id": "uuid"}
    """
    coffeebean_id = request.data.get('coffeebean_id')
    
    if not coffeebean_id:
        return Response(
            {'error': 'coffeebean_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        coffeebean = CoffeeBean.objects.get(id=coffeebean_id, is_active=True)
    except CoffeeBean.DoesNotExist:
        return Response(
            {'error': 'Coffee bean not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    entry, created = UserLibraryEntry.ensure_entry(
        user=request.user,
        coffeebean=coffeebean,
        added_by='manual'
    )
    
    serializer = UserLibraryEntrySerializer(entry)
    
    return Response(
        serializer.data,
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
    )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def archive_library_entry(request, entry_id):
    """
    Archive/unarchive a library entry.
    
    PATCH /api/reviews/library/{entry_id}/archive/
    Body: {"is_archived": true/false}
    """
    try:
        entry = UserLibraryEntry.objects.get(id=entry_id, user=request.user)
    except UserLibraryEntry.DoesNotExist:
        return Response(
            {'error': 'Library entry not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    is_archived = request.data.get('is_archived', True)
    entry.is_archived = is_archived
    entry.save(update_fields=['is_archived'])
    
    serializer = UserLibraryEntrySerializer(entry)
    return Response(serializer.data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_from_library(request, entry_id):
    """
    Remove coffee bean from user's library.
    
    DELETE /api/reviews/library/{entry_id}/
    """
    try:
        entry = UserLibraryEntry.objects.get(id=entry_id, user=request.user)
    except UserLibraryEntry.DoesNotExist:
        return Response(
            {'error': 'Library entry not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    entry.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Tag operations (read-only for users).
    
    list: Get all tags
    retrieve: Get a specific tag
    """
    
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        """Filter tags by category or search."""
        queryset = super().get_queryset()
        
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get most popular tags."""
        limit = int(request.query_params.get('limit', 20))
        
        tags = Tag.objects.annotate(
            usage_count=Count('reviews')
        ).order_by('-usage_count')[:limit]
        
        serializer = self.get_serializer(tags, many=True)
        return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_tag(request):
    """
    Create a new taste tag.
    
    POST /api/reviews/tags/create/
    Body: {"name": "fruity", "category": "flavor"}
    """
    serializer = TagSerializer(data=request.data)
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def bean_review_summary(request, bean_id):
    """
    Get comprehensive review summary for a coffee bean.
    
    GET /api/reviews/bean/{bean_id}/summary/
    """
    try:
        bean = CoffeeBean.objects.get(id=bean_id, is_active=True)
    except CoffeeBean.DoesNotExist:
        return Response(
            {'error': 'Coffee bean not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    reviews = Review.objects.filter(coffeebean=bean).select_related('author').prefetch_related('taste_tags')
    
    # Rating breakdown
    rating_breakdown = {}
    for i in range(1, 6):
        rating_breakdown[str(i)] = reviews.filter(rating=i).count()
    
    # Common tags
    common_tags = list(
        Tag.objects.filter(reviews__coffeebean=bean)
        .annotate(count=Count('reviews'))
        .order_by('-count')
        .values('id', 'name', 'count')[:10]
    )
    
    # Recent reviews
    recent_reviews = reviews.order_by('-created_at')[:5]
    
    data = {
        'bean_id': bean.id,
        'bean_name': f"{bean.roastery_name} - {bean.name}",
        'total_reviews': reviews.count(),
        'avg_rating': float(bean.avg_rating),
        'rating_breakdown': rating_breakdown,
        'common_tags': common_tags,
        'recent_reviews': ReviewSerializer(recent_reviews, many=True).data
    }
    
    serializer = BeanReviewSummarySerializer(data)
    return Response(serializer.data)