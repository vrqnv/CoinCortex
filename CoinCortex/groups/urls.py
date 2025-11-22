from django.urls import path
from . import views

urlpatterns = [
    path('', views.groups_list, name='groups_list'),
    path('create/', views.group_create, name='group_create'),
    path('<int:group_id>/', views.group_detail, name='group_detail'),
    path('<int:group_id>/subscribers/', views.group_subscribers, name='group_subscribers'),
    path('my/', views.my_groups, name='my_groups'),
]

