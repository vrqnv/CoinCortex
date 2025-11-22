from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('chat/', views.chat, name='chat'),
    path('profile/', views.profile, name='profile'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('loginout/', views.logout_view, name='loginout'),
    path('profile/<str:username>/', views.user_profile, name='user_profile'),
    path('chat/<int:chat_id>/', views.chat_detail, name='chat_detail'),  # Детальная страница чата
    path('chat/start/<str:username>/', views.start_chat, name='start_chat'),
    path('community/', views.community, name='community')
]
