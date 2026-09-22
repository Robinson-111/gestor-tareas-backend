from django.urls import path
from .views import ModuleListView

urlpatterns = [
    path('', ModuleListView.as_view(), name='module_list'),
]