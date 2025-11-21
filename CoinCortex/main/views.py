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
    return render(request, 'profile.html', {'user': request.user})

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


@login_required
def stena(request):
    """Лента новостей - все посты"""
    if request.method == 'POST':
        # Создание нового поста
        content = request.POST.get('content')
        if content:
            Post.objects.create(
                author=request.user,
                content=content,
                wall_owner=request.user
            )
            return redirect('stena')  # редирект после создания поста
    
    posts = Post.objects.all().order_by('-created')[:20]
    return render(request, 'stena.html', {'posts': posts}) 

