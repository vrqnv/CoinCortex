from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('chat/', views.chat, name='chat'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/delete/', views.delete_account, name='delete_account'),
    path('friends/', views.friends_page, name='friends'),
    path('notifications/', views.notifications, name='notifications'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('loginout/', views.logout_view, name='loginout'),
    path('profile/<str:username>/', views.user_profile, name='user_profile'),
    path('chat/<int:chat_id>/', views.chat_detail, name='chat_detail'),
    path('chat/start/<str:username>/', views.start_chat, name='start_chat'),
]
