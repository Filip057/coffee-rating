from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'reviews'

# Router for ViewSets
# Note: tags must be registered BEFORE empty prefix to avoid URL conflicts
router = DefaultRouter()
router.register(r'tags', views.TagViewSet, basename='tag')
router.register(r'', views.ReviewViewSet, basename='review')

urlpatterns = [
    # Review ViewSet routes (includes list, create, retrieve, update, destroy)
    # GET    /api/reviews/          - List all reviews
    # POST   /api/reviews/          - Create review
    # GET    /api/reviews/{id}/     - Get review
    # PUT    /api/reviews/{id}/     - Update review
    # PATCH  /api/reviews/{id}/     - Partial update
    # DELETE /api/reviews/{id}/     - Delete review
    
    # Custom review actions
    # GET    /api/reviews/my_reviews/        - Get current user's reviews
    # GET    /api/reviews/statistics/        - Get review statistics
    
    # User Library endpoints
    path('library/', views.user_library, name='user-library'),
    path('library/add/', views.add_to_library, name='add-to-library'),
    path('library/<uuid:entry_id>/archive/', views.archive_library_entry, name='archive-library-entry'),
    path('library/<uuid:entry_id>/', views.remove_from_library, name='remove-from-library'),
    
    # Tag endpoints
    # GET    /api/reviews/tags/         - List all tags
    # GET    /api/reviews/tags/{id}/    - Get tag
    # GET    /api/reviews/tags/popular/ - Get popular tags
    path('tags/create/', views.create_tag, name='create-tag'),
    
    # Bean review summary
    path('bean/<uuid:bean_id>/summary/', views.bean_review_summary, name='bean-review-summary'),
    
    # Include router URLs
    path('', include(router.urls)),
]