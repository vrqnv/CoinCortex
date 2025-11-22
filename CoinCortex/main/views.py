from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Post, Friendship, UserRating
from django.db.models import Q
from .models import Post, User, Friendship, Chat, Message


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
                messages.success(request, 'Пост успешно опубликован!')
                return redirect('profile')
        
        # Удаление поста
        elif 'delete_post' in request.POST:
            post_id = request.POST.get('delete_post')
            try:
                post = Post.objects.get(id=post_id, author=request.user)
                post.delete()
                messages.success(request, 'Пост удален')
            except Post.DoesNotExist:
                messages.error(request, 'Пост не найден')
            return redirect('profile')
        
        # Добавление в друзья
        elif 'add_friend' in request.POST:
            username = request.POST.get('add_friend')
            try:
                friend_user = User.objects.get(username=username)
                if friend_user == request.user:
                    messages.error(request, 'Нельзя добавить себя в друзья')
                else:
                    # Проверяем, нет ли уже существующей дружбы или заявки
                    existing_friendship = Friendship.objects.filter(
                        Q(from_user=request.user, to_user=friend_user) |
                        Q(from_user=friend_user, to_user=request.user)
                    ).first()
                    
                    if existing_friendship:
                        if existing_friendship.accepted:
                            messages.info(request, f'Вы уже друзья с {friend_user.username}')
                        else:
                            if existing_friendship.from_user == request.user:
                                messages.info(request, f'Вы уже отправили заявку {friend_user.username}')
                            else:
                                # Принимаем входящую заявку
                                existing_friendship.accepted = True
                                existing_friendship.save()
                                messages.success(request, f'Вы приняли заявку от {friend_user.username}')
                    else:
                        Friendship.objects.create(
                            from_user=request.user,
                            to_user=friend_user,
                            accepted=False
                        )
                        messages.success(request, f'Заявка отправлена {friend_user.username}')
                        
            except User.DoesNotExist:
                messages.error(request, 'Пользователь не найден')
            
            # Редирект на ту же страницу, откуда пришел запрос
            referer = request.META.get('HTTP_REFERER', 'profile')
            return redirect(referer)
        
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
                messages.success(request, f'Вы приняли заявку от {friendship.from_user.username}')
            except Friendship.DoesNotExist:
                messages.error(request, 'Заявка не найдена')
            
            # Редирект на ту же страницу, откуда пришел запрос
            referer = request.META.get('HTTP_REFERER', 'profile')
            return redirect(referer)
        
        # Удаление друга
        elif 'remove_friend' in request.POST:
            username = request.POST.get('remove_friend')
            try:
                friend_user = User.objects.get(username=username)
                # Удаляем обе стороны дружбы
                Friendship.objects.filter(
                    Q(from_user=request.user, to_user=friend_user) |
                    Q(from_user=friend_user, to_user=request.user),
                    accepted=True
                ).delete()
                messages.success(request, f'{friend_user.username} удален из друзей')
            except User.DoesNotExist:
                messages.error(request, 'Пользователь не найден')
            return redirect('profile')
        
        # Оценка друга
        elif 'rate_friend' in request.POST:
            friend_username = request.POST.get('rate_friend')
            rating_value = request.POST.get('rating')
            comment_text = request.POST.get('comment', '').strip()
            
            try:
                friend_user = User.objects.get(username=friend_username)
                # Проверяем, что это действительно друг
                is_friend = (
                    Friendship.objects.filter(
                        from_user=request.user,
                        to_user=friend_user,
                        accepted=True
                    ).exists() or
                    Friendship.objects.filter(
                        from_user=friend_user,
                        to_user=request.user,
                        accepted=True
                    ).exists()
                )
                
                if is_friend and friend_user != request.user:
                    rating_value = int(rating_value)
                    if 1 <= rating_value <= 10:
                        UserRating.objects.update_or_create(
                            rated_user=friend_user,
                            rater=request.user,
                            defaults={
                                'rating': rating_value,
                                'comment': comment_text
                            }
                        )
                        messages.success(request, f'Оценка {rating_value}/10 поставлена!')
                    else:
                        messages.error(request, 'Оценка должна быть от 1 до 10')
                else:
                    messages.error(request, 'Можно оценивать только своих друзей')
            except (User.DoesNotExist, ValueError):
                messages.error(request, 'Ошибка при постановке оценки')
            return redirect('profile')
    
    # Получаем последние посты текущего пользователя
    user_posts = Post.objects.filter(author=request.user).order_by('-created')[:10]
    
    # Получаем друзей пользователя
    friends_list = list(request.user.get_friends())
    
    # Получаем оценки, которые поставил текущий пользователь своим друзьям
    ratings_dict = {}
    for rating in UserRating.objects.filter(rater=request.user):
        ratings_dict[rating.rated_user.id] = {
            'rating': rating.rating,
            'comment': rating.comment
        }
    
    # Добавляем информацию об оценках к каждому другу
    friends_with_ratings = []
    for friend in friends_list:
        friend_data = {
            'user': friend,
            'rating': ratings_dict.get(friend.id, None)
        }
        friends_with_ratings.append(friend_data)
    
    # Получаем входящие заявки в друзья
    incoming_requests = Friendship.objects.filter(
        to_user=request.user,
        accepted=False
    )
    
    # Получаем исходящие заявки
    outgoing_requests = Friendship.objects.filter(
        from_user=request.user,
        accepted=False
    )
    
    # Поиск пользователей (если есть поисковый запрос)
    search_query = request.GET.get('search', '').strip()
    search_results = []
    if search_query:
        search_results = User.objects.filter(
            username__icontains=search_query
        ).exclude(id=request.user.id).distinct()[:10]
    
    return render(request, 'profile.html', {
        'user': request.user,
        'posts': user_posts,
        'friends': friends_with_ratings,
        'incoming_requests': incoming_requests,
        'outgoing_requests': outgoing_requests,
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
        return redirect('login')
    return render(request, 'registration/logout.html')

@login_required
def user_profile(request, username):
    """Просмотр профиля другого пользователя"""
    try:
        profile_user = User.objects.get(username=username)
        
        # Если пользователь смотрит свой профиль - редирект на свой профиль
        if profile_user == request.user:
            return redirect('profile')
        
        # Проверяем, является ли пользователь другом
        is_friend = Friendship.objects.filter(
            (Q(from_user=request.user, to_user=profile_user) | 
             Q(from_user=profile_user, to_user=request.user)),
            accepted=True
        ).exists()
        
        # Получаем посты пользователя
        user_posts = Post.objects.filter(author=profile_user).order_by('-created')[:10]
        
        # Проверяем, отправил ли текущий пользователь заявку в друзья
        friend_request_sent = Friendship.objects.filter(
            from_user=request.user,
            to_user=profile_user,
            accepted=False
        ).exists()
        
        # Проверяем, есть ли входящая заявка от этого пользователя
        incoming_request = Friendship.objects.filter(
            from_user=profile_user,
            to_user=request.user,
            accepted=False
        ).first()
        
        context = {
            'profile_user': profile_user,
            'posts': user_posts,
            'is_friend': is_friend,
            'friend_request_sent': friend_request_sent,
            'incoming_request': incoming_request,
        }
        
        return render(request, 'user_profile.html', context)
        
    except User.DoesNotExist:
        messages.error(request, 'Пользователь не найден')
        return redirect('profile')
    
@login_required
def chat(request):
    """Страница со списком чатов"""
    # Получаем все чаты пользователя
    chats = Chat.objects.filter(participants=request.user).prefetch_related('participants', 'messages')
    
    return render(request, 'chat.html', {
        'chats': chats
    })

@login_required
def chat_detail(request, chat_id):
    """Детальная страница чата"""
    try:
        chat = Chat.objects.get(id=chat_id, participants=request.user)
        other_user = chat.get_other_participant(request.user)
        
        if request.method == 'POST':
            text = request.POST.get('text', '').strip()
            if text:
                Message.objects.create(
                    chat=chat,
                    sender=request.user,
                    text=text
                )
                # Обновляем время последнего изменения чата
                chat.save()  # Это обновит поле updated
                return redirect('chat_detail', chat_id=chat.id)
        
        # Получаем сообщения чата
        messages = chat.messages.all()
        
        # Помечаем сообщения как прочитанные
        chat.messages.filter(sender=other_user, read=False).update(read=True)
        
        return render(request, 'chat_detail.html', {
            'chat': chat,
            'other_user': other_user,
            'messages': messages
        })
        
    except Chat.DoesNotExist:
        messages.error(request, 'Чат не найден')
        return redirect('chat')

@login_required
def start_chat(request, username):
    """Начать новый чат с пользователем"""
    try:
        other_user = User.objects.get(username=username)
        if other_user == request.user:
            messages.error(request, 'Нельзя начать чат с собой')
            return redirect('chat')
        
        chat = request.user.get_or_create_chat(other_user)
        return redirect('chat_detail', chat_id=chat.id)
        
    except User.DoesNotExist:
        messages.error(request, 'Пользователь не найден')
        return redirect('chat')
