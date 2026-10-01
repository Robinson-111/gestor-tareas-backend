from django.urls import path
from .views import ModuleListView, ModuleDetailView, MembersModuleView, ClaimModuleOwnershipView

urlpatterns = [
    path('', ModuleListView.as_view(), name='modules_list'),
    path('<int:id>/',ModuleDetailView.as_view() , name='module_detail'),
    path('<int:id>/members/', MembersModuleView.as_view(), name='members_module_list'),
    path('<int:id>/members/<int:user_id>/', MembersModuleView.as_view(), name='members_module_delete'),
    path('<int:id>/claim', ClaimModuleOwnershipView.as_view(), name='module_claim_ownership'),
]