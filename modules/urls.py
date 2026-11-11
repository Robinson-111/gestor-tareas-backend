from django.urls import path
from .views import (
    ModuleListView,
    ModuleExploreListView,
    ModuleJoinView,
    ModuleClaimableListView,
    ModuleDetailView,
    MembersModuleView,
    ClaimModuleOwnershipView,
    LeaveModuleView
)

urlpatterns = [
    path('', ModuleListView.as_view(), name='modules_list'),
    path('explore/', ModuleExploreListView.as_view(), name='modules_explore'),
    path('claimable/', ModuleClaimableListView.as_view(), name='modules_claimable'),
    path('<int:id>/', ModuleDetailView.as_view(), name='module_detail'),
    path('<int:id>/join/', ModuleJoinView.as_view(), name='module_join'),
    path('<int:id>/members/', MembersModuleView.as_view(), name='members_module_list'),
    path('<int:id>/members/<int:user_id>/', MembersModuleView.as_view(), name='members_module_delete'),
    path('<int:id>/leave/', LeaveModuleView.as_view(), name='module_leave'),
    path('<int:id>/claim', ClaimModuleOwnershipView.as_view(), name='module_claim_ownership'),
]
