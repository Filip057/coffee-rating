from rest_framework import status, generics, viewsets, serializers as drf_serializers
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db import transaction
from django.db.models import Count, Avg, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
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


# Request/Response serializers for API documentation
class AddToLibraryRequestSerializer(drf_serializers.Serializer):
    coffeebean_id = drf_serializers.UUIDField(help_text="UUID of coffee bean to add")


class ArchiveLibraryRequestSerializer(drf_serializers.Serializer):
    is_archived = drf_serializers.BooleanField(default=True)


class ErrorResponseSerializer(drf_serializers.Serializer):
    error = drf_serializers.CharField()


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
    
    def perform_create(self, serializer):
        """Create review using service layer."""
        from apps.reviews.services import create_review, add_to_library
        from apps.reviews.services.exceptions import (
            DuplicateReviewError,
            BeanNotFoundError,
            InvalidRatingError,
            InvalidContextError,
            GroupMembershipRequiredError,
        )
        from rest_framework.exceptions import ValidationError

        try:
            review = create_review(
                author=self.request.user,
                coffeebean_id=serializer.validated_data['coffeebean'].id,
                rating=serializer.validated_data['rating'],
                aroma_score=serializer.validated_data.get('aroma_score'),
                flavor_score=serializer.validated_data.get('flavor_score'),
                acidity_score=serializer.validated_data.get('acidity_score'),
                body_score=serializer.validated_data.get('body_score'),
                aftertaste_score=serializer.validated_data.get('aftertaste_score'),
                notes=serializer.validated_data.get('notes', ''),
                brew_method=serializer.validated_data.get('brew_method', ''),
                taste_tag_ids=[tag.id for tag in serializer.validated_data.get('taste_tags', [])],
                context=serializer.validated_data.get('context', 'personal'),
                group_id=serializer.validated_data.get('group').id if serializer.validated_data.get('group') else None,
                would_buy_again=serializer.validated_data.get('would_buy_again'),
            )

            # Auto-add to library
            add_to_library(
                user=self.request.user,
                coffeebean_id=review.coffeebean.id,
                added_by='review'
            )

            # Update aggregate rating (asynchronous)
            transaction.on_commit(lambda: review.coffeebean.update_aggregate_rating())

        except (DuplicateReviewError, BeanNotFoundError, InvalidRatingError,
                InvalidContextError, GroupMembershipRequiredError) as e:
            raise ValidationError(str(e))

        serializer.instance = review
    
    def perform_update(self, serializer):
        """Update review using service layer."""
        from apps.reviews.services import update_review
        from apps.reviews.services.exceptions import (
            ReviewNotFoundError,
            UnauthorizedReviewActionError,
            InvalidRatingError,
        )
        from rest_framework.exceptions import ValidationError

        try:
            review = update_review(
                review_id=serializer.instance.id,
                user=self.request.user,
                rating=serializer.validated_data.get('rating'),
                aroma_score=serializer.validated_data.get('aroma_score'),
                flavor_score=serializer.validated_data.get('flavor_score'),
                acidity_score=serializer.validated_data.get('acidity_score'),
                body_score=serializer.validated_data.get('body_score'),
                aftertaste_score=serializer.validated_data.get('aftertaste_score'),
                notes=serializer.validated_data.get('notes'),
                brew_method=serializer.validated_data.get('brew_method'),
                taste_tag_ids=[tag.id for tag in serializer.validated_data.get('taste_tags', [])] if 'taste_tags' in serializer.validated_data else None,
                would_buy_again=serializer.validated_data.get('would_buy_again'),
            )

            # Update aggregate rating (asynchronous)
            transaction.on_commit(lambda: review.coffeebean.update_aggregate_rating())

        except (ReviewNotFoundError, UnauthorizedReviewActionError, InvalidRatingError) as e:
            raise ValidationError(str(e))

        serializer.instance = review
    
    def perform_destroy(self, instance):
        """Delete review using service layer."""
        from apps.reviews.services import delete_review
        from apps.reviews.services.exceptions import (
            ReviewNotFoundError,
            UnauthorizedReviewActionError,
        )
        from rest_framework.exceptions import ValidationError

        try:
            coffeebean = instance.coffeebean
            delete_review(review_id=instance.id, user=self.request.user)

            # Update aggregate rating (asynchronous)
            transaction.on_commit(lambda: coffeebean.update_aggregate_rating())

        except (ReviewNotFoundError, UnauthorizedReviewActionError) as e:
            raise ValidationError(str(e))
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_reviews(self, request):
        """Get current user's reviews using service layer."""
        from apps.reviews.services import get_user_reviews

        reviews = get_user_reviews(user=request.user)
        page = self.paginate_queryset(reviews)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get review statistics using service layer."""
        from apps.reviews.services import get_review_statistics

        # Get optional filters
        user_id = request.query_params.get('user_id')
        bean_id = request.query_params.get('bean_id')

        # Call service
        data = get_review_statistics(
            user_id=user_id,
            bean_id=bean_id
        )

        serializer = ReviewStatisticsSerializer(data)
        return Response(serializer.data)


@extend_schema(
    parameters=[
        OpenApiParameter('archived', OpenApiTypes.BOOL, description='Show archived entries', default=False),
        OpenApiParameter('search', OpenApiTypes.STR, description='Search in bean name or roastery'),
    ],
    responses={200: UserLibraryEntrySerializer(many=True)},
    description="Get user's coffee library with their saved beans.",
    tags=['reviews'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_library(request):
    """Get user's coffee library using service layer."""
    from apps.reviews.services import get_user_library

    archived = request.GET.get('archived', 'false').lower() == 'true'
    search = request.GET.get('search', '')

    library = get_user_library(
        user=request.user,
        is_archived=archived,
        search=search
    )

    serializer = UserLibraryEntrySerializer(library, many=True)
    return Response(serializer.data)


@extend_schema(
    request=AddToLibraryRequestSerializer,
    responses={
        201: UserLibraryEntrySerializer,
        200: UserLibraryEntrySerializer,
        400: ErrorResponseSerializer,
        404: ErrorResponseSerializer,
    },
    description="Manually add a coffee bean to user's library. Returns 200 if already exists.",
    tags=['reviews'],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_library(request):
    """Manually add coffee bean to user's library using service layer."""
    from apps.reviews.services import add_to_library as add_to_library_service
    from apps.reviews.services.exceptions import BeanNotFoundError

    coffeebean_id = request.data.get('coffeebean_id')

    if not coffeebean_id:
        return Response(
            {'error': 'coffeebean_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        entry, created = add_to_library_service(
            user=request.user,
            coffeebean_id=coffeebean_id,
            added_by='manual'
        )

        serializer = UserLibraryEntrySerializer(entry)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    except BeanNotFoundError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_404_NOT_FOUND
        )


@extend_schema(
    request=ArchiveLibraryRequestSerializer,
    responses={
        200: UserLibraryEntrySerializer,
        404: ErrorResponseSerializer,
    },
    description="Archive or unarchive a library entry.",
    tags=['reviews'],
)
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def archive_library_entry(request, entry_id):
    """Archive/unarchive a library entry using service layer."""
    from apps.reviews.services import archive_library_entry as archive_service
    from apps.reviews.services.exceptions import LibraryEntryNotFoundError

    try:
        is_archived = request.data.get('is_archived', True)
        entry = archive_service(
            entry_id=entry_id,
            user=request.user,
            is_archived=is_archived
        )

        serializer = UserLibraryEntrySerializer(entry)
        return Response(serializer.data)

    except LibraryEntryNotFoundError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_404_NOT_FOUND
        )


@extend_schema(
    responses={
        204: None,
        404: ErrorResponseSerializer,
    },
    description="Remove a coffee bean from user's library.",
    tags=['reviews'],
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_from_library(request, entry_id):
    """Remove coffee bean from user's library using service layer."""
    from apps.reviews.services import remove_from_library as remove_service
    from apps.reviews.services.exceptions import LibraryEntryNotFoundError

    try:
        remove_service(entry_id=entry_id, user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    except LibraryEntryNotFoundError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_404_NOT_FOUND
        )


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
        """Get most popular tags using service layer."""
        from apps.reviews.services import get_popular_tags

        limit = int(request.query_params.get('limit', 20))
        tags = get_popular_tags(limit=limit)

        serializer = self.get_serializer(tags, many=True)
        return Response(serializer.data)


@extend_schema(
    request=TagSerializer,
    responses={
        201: TagSerializer,
        400: ErrorResponseSerializer,
    },
    description="Create a new taste tag for coffee reviews.",
    tags=['reviews'],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_tag(request):
    """Create a new taste tag using service layer."""
    from apps.reviews.services import create_tag as create_tag_service
    from django.db import IntegrityError

    serializer = TagSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        tag = create_tag_service(
            name=serializer.validated_data['name'],
            category=serializer.validated_data.get('category', '')
        )

        response_serializer = TagSerializer(tag)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    except IntegrityError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(
    responses={
        200: BeanReviewSummarySerializer,
        404: ErrorResponseSerializer,
    },
    description="Get comprehensive review summary for a coffee bean including rating breakdown, common tags, and recent reviews.",
    tags=['reviews'],
)
@api_view(['GET'])
def bean_review_summary(request, bean_id):
    """Get comprehensive review summary for a coffee bean using service layer."""
    from apps.reviews.services import get_bean_review_summary
    from apps.reviews.services.exceptions import BeanNotFoundError

    try:
        data = get_bean_review_summary(bean_id=bean_id)

        # Add recent reviews (not in service as it's view-specific)
        reviews = Review.objects.filter(
            coffeebean_id=bean_id
        ).select_related('author').prefetch_related('taste_tags').order_by('-created_at')[:5]

        data['recent_reviews'] = ReviewSerializer(reviews, many=True).data

        serializer = BeanReviewSummarySerializer(data)
        return Response(serializer.data)

    except BeanNotFoundError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_404_NOT_FOUND
        )