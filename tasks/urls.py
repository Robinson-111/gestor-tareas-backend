from django.urls import path

from tasks.views import TaskDetailView, TaskListCreateView

urlpatterns = [
    path('', TaskListCreateView.as_view(), name='module_tasks'),
    path('<int:task_id>/', TaskDetailView.as_view(), name='module_task_detail'),
]
