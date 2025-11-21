from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Post

def index(request):
    return render(request, 'index.html')

@login_required
def chat(request):
    return render(request, 'chat.html')

@login_required
def profile(request):
    """Профиль пользователя с возможностью создания и удаления постов"""
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
    
    # Получаем последние посты текущего пользователя
    user_posts = Post.objects.filter(author=request.user).order_by('-created')[:10]
    return render(request, 'profile.html', {
        'user': request.user,
        'posts': user_posts
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
