from django.urls import path
from account.views import UserListView, UserDetailView

urlpatterns = [
    path('', UserListView.as_view(), name = 'users'),
    path('<int:id>/', UserDetailView.as_view(), name='user')
]