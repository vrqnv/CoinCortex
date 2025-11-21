from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Post, User, Friendship

def index(request):
    """Главная страница с лентой постов от сообществ"""
    # Получаем последние посты (можно позже фильтровать по сообществам)
    community_posts = Post.objects.all().order_by('-created')[:20]
    
    return render(request, 'index.html', {
        'community_posts': community_posts
    })

@login_required
def chat(request):
    return render(request, 'chat.html')

@login_required
def profile(request):
    """Профиль пользователя с постами, друзьями и поиском"""
    if request.method == 'POST':
        # Создание нового поста
        if 'content' in request.POST:
            content = request.POST.get('content')
            if content and content.strip():
                Post.objects.create(
                    author=request.user,
                    content=content.strip(),
                    wall_owner=request.user
                )
                return redirect('profile')
        
        # Удаление поста
        elif 'delete_post' in request.POST:
            post_id = request.POST.get('delete_post')
            try:
                post = Post.objects.get(id=post_id, author=request.user)
                post.delete()
                return redirect('profile')
            except Post.DoesNotExist:
                pass
        
        # Добавление в друзья
        elif 'add_friend' in request.POST:
            username = request.POST.get('add_friend')
            try:
                friend_user = User.objects.get(username=username)
                if friend_user != request.user:
                    Friendship.objects.get_or_create(
                        from_user=request.user,
                        to_user=friend_user,
                        defaults={'accepted': False}
                    )
            except User.DoesNotExist:
                pass
            return redirect('profile')
        
        # Принятие заявки в друзья
        elif 'accept_friend' in request.POST:
            friend_id = request.POST.get('accept_friend')
            try:
                friendship = Friendship.objects.get(
                    id=friend_id,
                    to_user=request.user,
                    accepted=False
                )
                friendship.accepted = True
                friendship.save()
            except Friendship.DoesNotExist:
                pass
            return redirect('profile')
    
    # Получаем последние посты текущего пользователя
    user_posts = Post.objects.filter(author=request.user).order_by('-created')[:10]
    
    # Получаем друзей пользователя
    friends = request.user.get_friends()
    
    # Получаем входящие заявки в друзья
    incoming_requests = Friendship.objects.filter(
        to_user=request.user,
        accepted=False
    )
    
    # Поиск пользователей (если есть поисковый запрос)
    search_query = request.GET.get('search', '')
    search_results = []
    if search_query:
        search_results = User.objects.filter(
            username__icontains=search_query
        ).exclude(id=request.user.id)[:10]
    
    return render(request, 'profile.html', {
        'user': request.user,
        'posts': user_posts,
        'friends': friends,
        'incoming_requests': incoming_requests,
        'search_results': search_results,
        'search_query': search_query
    })

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
        else:
            messages.error(request, 'Исправьте ошибки в форме')
    else:
        form = UserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('index')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль')
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

@login_required
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return redirect('login')  # Изменил на 'login' вместо 'index'
    return render(request, 'registration/loginout.html')  # Создайте этот шаблон
