from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'groups'

# Router for ViewSets
router = DefaultRouter()
router.register(r'', views.GroupViewSet, basename='group')

urlpatterns = [
    # Group ViewSet routes
    # GET    /api/groups/              - List user's groups
    # POST   /api/groups/              - Create group
    # GET    /api/groups/{id}/         - Get group details
    # PUT    /api/groups/{id}/         - Update group (admin)
    # PATCH  /api/groups/{id}/         - Partial update (admin)
    # DELETE /api/groups/{id}/         - Delete group (owner)
    
    # Custom group actions
    # GET    /api/groups/{id}/members/              - List members
    # POST   /api/groups/{id}/join/                 - Join with invite code
    # POST   /api/groups/{id}/leave/                - Leave group
    # POST   /api/groups/{id}/regenerate_invite/    - Regenerate invite code (admin)
    # POST   /api/groups/{id}/update_member_role/   - Update member role (admin)
    # DELETE /api/groups/{id}/remove_member/        - Remove member (admin)
    # GET    /api/groups/{id}/library/              - Get group library
    # POST   /api/groups/{id}/add_to_library/       - Add bean to library
    
    # Additional endpoints
    path('my/', views.my_groups, name='my-groups'),
    
    # Include router URLs
    path('', include(router.urls)),
]