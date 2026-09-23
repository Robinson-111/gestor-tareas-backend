from django.urls import path
from .views import ModuleListView, ModuleDetailView

urlpatterns = [
    path('', ModuleListView.as_view(), name='modules_list'),
    path('<int:id>/',ModuleDetailView.as_view() ,name='module_detail')
]