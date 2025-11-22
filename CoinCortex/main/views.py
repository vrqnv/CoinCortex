from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import (
    Post,
    PostLike,
    PostComment,
    Friendship,
    Chat,
    Message,
    Notification,
    Community,
)
from .forms import CustomUserCreationForm


def index(request):
    """Главная страница с лентой постов от сообществ"""
    # Получаем последние посты (можно позже фильтровать по сообществам)
    community_posts = Post.objects.all().order_by("-created")[:20]

    return render(request, "index.html", {"community_posts": community_posts})


@login_required
def profile(request):
    """Профиль пользователя с постами, друзьями и поиском"""
    if request.method == "POST":
        # Создание нового поста
        if "content" in request.POST:
            content = request.POST.get("content")
            image = request.FILES.get("image")
            if content and content.strip():
                post = Post.objects.create(
                    author=request.user,
                    content=content.strip(),
                    wall_owner=request.user,
                )
                if image:
                    post.image = image
                    post.save()
                messages.success(request, "Пост успешно опубликован!")
                return redirect("profile")

        # Удаление поста
        elif "delete_post" in request.POST:
            post_id = request.POST.get("delete_post")
            try:
                post = Post.objects.get(id=post_id, author=request.user)
                post.delete()
                messages.success(request, "Пост удален")
            except Post.DoesNotExist:
                messages.error(request, "Пост не найден")
            return redirect("profile")

        # Добавление в друзья
        elif "add_friend" in request.POST:
            username = request.POST.get("add_friend")
            try:
                friend_user = User.objects.get(username=username)
                if friend_user == request.user:
                    messages.error(request, "Нельзя добавить себя в друзья")
                else:
                    # Проверяем, нет ли уже существующей дружбы или заявки
                    existing_friendship = Friendship.objects.filter(
                        Q(from_user=request.user, to_user=friend_user)
                        | Q(from_user=friend_user, to_user=request.user)
                    ).first()

                    if existing_friendship:
                        if existing_friendship.accepted:
                            messages.info(
                                request, f"Вы уже друзья с {friend_user.username}"
                            )
                        else:
                            if existing_friendship.from_user == request.user:
                                messages.info(
                                    request,
                                    f"Вы уже отправили заявку {friend_user.username}",
                                )
                            else:
                                # Принимаем входящую заявку
                                existing_friendship.accepted = True
                                existing_friendship.save()
                                messages.success(
                                    request,
                                    f"Вы приняли заявку от {friend_user.username}",
                                )
                    else:
                        Friendship.objects.create(
                            from_user=request.user, to_user=friend_user, accepted=False
                        )
                        messages.success(
                            request, f"Заявка отправлена {friend_user.username}"
                        )

            except User.DoesNotExist:
                messages.error(request, "Пользователь не найден")

            # Редирект на ту же страницу, откуда пришел запрос
            referer = request.META.get("HTTP_REFERER", "profile")
            return redirect(referer)

        # Принятие заявки в друзья
        elif "accept_friend" in request.POST:
            friend_id = request.POST.get("accept_friend")
            try:
                friendship = Friendship.objects.get(
                    id=friend_id, to_user=request.user, accepted=False
                )
                friendship.accepted = True
                friendship.save()
                messages.success(
                    request, f"Вы приняли заявку от {friendship.from_user.username}"
                )
            except Friendship.DoesNotExist:
                messages.error(request, "Заявка не найдена")

            # Редирект на ту же страницу, откуда пришел запрос
            referer = request.META.get("HTTP_REFERER", "profile")
            return redirect(referer)

        # Удаление друга
        elif "remove_friend" in request.POST:
            username = request.POST.get("remove_friend")
            try:
                friend_user = User.objects.get(username=username)
                # Удаляем обе стороны дружбы
                Friendship.objects.filter(
                    Q(from_user=request.user, to_user=friend_user)
                    | Q(from_user=friend_user, to_user=request.user),
                    accepted=True,
                ).delete()
                messages.success(request, f"{friend_user.username} удален из друзей")
            except User.DoesNotExist:
                messages.error(request, "Пользователь не найден")
            return redirect("profile")

        # Лайк поста
        elif "like_post" in request.POST:
            post_id = request.POST.get("like_post")
            try:
                if post_id.startswith("group_"):
                    # Лайк поста группы
                    from groups.models import GroupPost, GroupPostLike

                    post_id = post_id.replace("group_", "")
                    post = GroupPost.objects.get(id=post_id)
                    like, created = GroupPostLike.objects.get_or_create(
                        post=post, user=request.user
                    )
                    if not created:
                        like.delete()
                        messages.info(request, "Лайк убран")
                    else:
                        if post.author != request.user:
                            Notification.objects.create(
                                user=post.author,
                                notification_type="group_like",
                                from_user=request.user,
                                group_post=post,
                            )
                        messages.success(request, "Лайк поставлен")
                else:
                    # Лайк обычного поста
                    post = Post.objects.get(id=post_id)
                    like, created = PostLike.objects.get_or_create(
                        post=post, user=request.user
                    )
                    if not created:
                        like.delete()
                        messages.info(request, "Лайк убран")
                    else:
                        if post.author != request.user:
                            Notification.objects.create(
                                user=post.author,
                                notification_type="like",
                                from_user=request.user,
                                post=post,
                            )
                        messages.success(request, "Лайк поставлен")
            except (Post.DoesNotExist, GroupPost.DoesNotExist):
                messages.error(request, "Пост не найден")
            referer = request.META.get("HTTP_REFERER", "index")
            return redirect(referer)

        # Комментарий к посту
        elif "comment_post" in request.POST:
            post_id = request.POST.get("comment_post")
            comment_text = request.POST.get("comment_text", "").strip()
            if comment_text:
                try:
                    if post_id.startswith("group_"):
                        # Комментарий к посту группы
                        from groups.models import GroupPost, GroupPostComment

                        post_id = post_id.replace("group_", "")
                        post = GroupPost.objects.get(id=post_id)
                        GroupPostComment.objects.create(
                            post=post, author=request.user, content=comment_text
                        )
                        if post.author != request.user:
                            Notification.objects.create(
                                user=post.author,
                                notification_type="group_comment",
                                from_user=request.user,
                                group_post=post,
                            )
                        messages.success(request, "Комментарий добавлен")
                    else:
                        # Комментарий к обычному посту
                        post = Post.objects.get(id=post_id)
                        PostComment.objects.create(
                            post=post, author=request.user, content=comment_text
                        )
                        if post.author != request.user:
                            Notification.objects.create(
                                user=post.author,
                                notification_type="comment",
                                from_user=request.user,
                                post=post,
                            )
                        messages.success(request, "Комментарий добавлен")
                except (Post.DoesNotExist, GroupPost.DoesNotExist):
                    messages.error(request, "Пост не найден")
            referer = request.META.get("HTTP_REFERER", "index")
            return redirect(referer)

    # Получаем последние посты текущего пользователя с оптимизацией
    user_posts = (
        Post.objects.filter(author=request.user)
        .select_related("author", "wall_owner")
        .order_by("-created")[:10]
    )

    # Добавляем информацию о лайках для каждого поста
    posts_with_info = []
    for post in user_posts:
        posts_with_info.append(
            {
                "post": post,
                "is_liked": post.is_liked_by(request.user),
                "likes_count": post.get_likes_count(),
                "comments_count": post.get_comments_count(),
                "comments": post.comments.select_related("author").all()[
                    :5
                ],  # Последние 5 комментариев
            }
        )

    # Получаем друзей пользователя с оптимизацией
    sent_friends = User.objects.filter(
        friendship_requests_received__from_user=request.user,
        friendship_requests_received__accepted=True,
    ).select_related("profile")
    received_friends = User.objects.filter(
        friendship_requests_sent__to_user=request.user,
        friendship_requests_sent__accepted=True,
    ).select_related("profile")
    friends_list = list(sent_friends.union(received_friends))

    # Получаем входящие заявки в друзья
    incoming_requests = Friendship.objects.filter(to_user=request.user, accepted=False)

    # Получаем исходящие заявки
    outgoing_requests = Friendship.objects.filter(
        from_user=request.user, accepted=False
    )

    # Поиск пользователей (если есть поисковый запрос)
    search_query = request.GET.get("search", "").strip()
    search_results = []
    if search_query:
        search_results = (
            User.objects.filter(username__icontains=search_query)
            .exclude(id=request.user.id)
            .distinct()[:10]
        )

    return render(
        request,
        "profile.html",
        {
            "user": request.user,
            "posts": posts_with_info,
            "friends": friends_list,
            "incoming_requests": incoming_requests,
            "outgoing_requests": outgoing_requests,
            "search_results": search_results,
            "search_query": search_query,
        },
    )


def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Регистрация успешна!")
            return redirect("index")
        else:
            messages.error(request, "Исправьте ошибки в форме")
    else:
        form = CustomUserCreationForm()

    return render(request, "registration/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("index")
        else:
            messages.error(request, "Неверное имя пользователя или пароль")
    else:
        form = AuthenticationForm()
    return render(request, "registration/login.html", {"form": form})


@login_required
def logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect("login")
    return render(request, "registration/logout.html")


@login_required
def user_profile(request, username):
    """Просмотр профиля другого пользователя"""
    try:
        profile_user = User.objects.get(username=username)

        # Если пользователь смотрит свой профиль - редирект на свой профиль
        if profile_user == request.user:
            return redirect("profile")

        # Проверяем, является ли пользователь другом
        is_friend = Friendship.objects.filter(
            (
                Q(from_user=request.user, to_user=profile_user)
                | Q(from_user=profile_user, to_user=request.user)
            ),
            accepted=True,
        ).exists()

        # Получаем посты пользователя с оптимизацией
        user_posts = (
            Post.objects.filter(author=profile_user)
            .select_related("author", "wall_owner")
            .order_by("-created")[:10]
        )

        # Проверяем, отправил ли текущий пользователь заявку в друзья
        friend_request_sent = Friendship.objects.filter(
            from_user=request.user, to_user=profile_user, accepted=False
        ).exists()

        # Проверяем, есть ли входящая заявка от этого пользователя
        incoming_request = Friendship.objects.filter(
            from_user=profile_user, to_user=request.user, accepted=False
        ).first()

        context = {
            "profile_user": profile_user,
            "posts": user_posts,
            "is_friend": is_friend,
            "friend_request_sent": friend_request_sent,
            "incoming_request": incoming_request,
        }

        return render(request, "user_profile.html", context)

    except User.DoesNotExist:
        messages.error(request, "Пользователь не найден")
        return redirect("profile")


@login_required
def chat(request):
    """Страница со списком чатов"""
    # Получаем все чаты пользователя с оптимизацией
    chats = (
        Chat.objects.filter(participants=request.user)
        .prefetch_related("participants", "messages__sender")
        .order_by("-updated")
    )

    # Добавляем информацию о непрочитанных сообщениях для каждого чата
    chats_with_info = []
    total_unread = 0
    for chat in chats:
        other_user = chat.get_other_participant(request.user)
        unread_count = chat.messages.filter(sender=other_user, read=False).count()
        total_unread += unread_count
        last_message = chat.get_last_message()

        chats_with_info.append(
            {
                "chat": chat,
                "other_user": other_user,
                "unread_count": unread_count,
                "last_message": last_message,
            }
        )

    # Поиск друзей для нового чата
    search_query = request.GET.get("search", "").strip()
    search_results = []
    if search_query:
        # Ищем среди друзей
        friends = request.user.get_friends()
        search_results = friends.filter(
            username__icontains=search_query
        ).select_related("profile")[:10]

    return render(
        request,
        "chat.html",
        {
            "chats": chats_with_info,
            "search_results": search_results,
            "search_query": search_query,
            "total_unread": total_unread,
        },
    )


@login_required
def chat_detail(request, chat_id):
    """Детальная страница чата"""
    try:
        chat = Chat.objects.get(id=chat_id, participants=request.user)
        other_user = chat.get_other_participant(request.user)

        if request.method == "POST":
            text = request.POST.get("text", "").strip()
            if text:
                Message.objects.create(chat=chat, sender=request.user, text=text)
                # Обновляем время последнего изменения чата
                chat.save()  # Это обновит поле updated
                return redirect("chat_detail", chat_id=chat.id)

        # Получаем сообщения чата с оптимизацией
        messages = chat.messages.select_related("sender").all()

        # Помечаем сообщения как прочитанные
        chat.messages.filter(sender=other_user, read=False).update(read=True)

        return render(
            request,
            "chat_detail.html",
            {"chat": chat, "other_user": other_user, "messages": messages},
        )

    except Chat.DoesNotExist:
        messages.error(request, "Чат не найден")
        return redirect("chat")


@login_required
def start_chat(request, username):
    """Начать новый чат с пользователем"""
    try:
        other_user = User.objects.get(username=username)
        if other_user == request.user:
            messages.error(request, "Нельзя начать чат с собой")
            return redirect("chat")

        chat = request.user.get_or_create_chat(other_user)
        return redirect("chat_detail", chat_id=chat.id)

    except User.DoesNotExist:
        messages.error(request, "Пользователь не найден")
        return redirect("chat")


@login_required
def edit_profile(request):
    """Редактирование профиля"""
    profile = request.user.profile

    if request.method == "POST":
        profile.first_name = request.POST.get("first_name", "")
        profile.last_name = request.POST.get("last_name", "")
        profile.bio = request.POST.get("bio", "")
        birth_date = request.POST.get("birth_date")
        if birth_date:
            profile.birth_date = birth_date
        if "avatar" in request.FILES:
            profile.avatar = request.FILES["avatar"]
        profile.save()
        messages.success(request, "Профиль успешно обновлен!")
        return redirect("profile")

    return render(request, "registration/edit_profile.html", {"profile": profile})


@login_required
def delete_account(request):
    """Удаление аккаунта"""
    if request.method == "POST":
        if "confirm" in request.POST:
            request.user.delete()
            messages.success(request, "Ваш аккаунт был удален")
            return redirect("index")

    return render(request, "registration/delete_account.html")


@login_required
def friends_page(request):
    """Страница со списком друзей"""
    # Получаем всех друзей
    sent_friends = User.objects.filter(
        friendship_requests_received__from_user=request.user,
        friendship_requests_received__accepted=True,
    ).select_related("profile")
    received_friends = User.objects.filter(
        friendship_requests_sent__to_user=request.user,
        friendship_requests_sent__accepted=True,
    ).select_related("profile")
    friends_list = list(sent_friends.union(received_friends))

    # Получаем входящие заявки
    incoming_requests = Friendship.objects.filter(
        to_user=request.user, accepted=False
    ).select_related("from_user")

    # Получаем исходящие заявки
    outgoing_requests = Friendship.objects.filter(
        from_user=request.user, accepted=False
    ).select_related("to_user")

    return render(
        request,
        "friends.html",
        {
            "friends": friends_list,
            "incoming_requests": incoming_requests,
            "outgoing_requests": outgoing_requests,
        },
    )


@login_required
def notifications(request):
    """Страница уведомлений"""
    user_notifications = (
        Notification.objects.filter(user=request.user)
        .select_related("from_user", "post", "group_post")
        .order_by("-created")[:50]
    )

    # Помечаем уведомления как прочитанные
    Notification.objects.filter(user=request.user, read=False).update(read=True)

    return render(request, "notifications.html", {"notifications": user_notifications})


@login_required
def communities(request):
    """Список сообществ"""
    communities_list = (
        Community.objects.all()
        .select_related("creator")
        .prefetch_related("members")
        .order_by("-created")
    )

    # Поиск
    search_query = request.GET.get("search", "").strip()
    if search_query:
        communities_list = communities_list.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )

    return render(
        request,
        "communities/communities.html",
        {"communities": communities_list, "search_query": search_query},
    )


@login_required
def community_detail(request, community_id):
    """Детальная страница сообщества"""
    community = get_object_or_404(Community, id=community_id)
    is_member = community.members.filter(id=request.user.id).exists()

    # Получаем посты сообщества
    posts = (
        Post.objects.filter(community=community)
        .select_related("author")
        .order_by("-created")[:20]
    )

    if request.method == "POST":
        # Создание поста
        if "content" in request.POST:
            content = request.POST.get("content", "").strip()
            if content:
                post = Post.objects.create(
                    author=request.user,
                    content=content,
                    wall_owner=request.user,
                    community=community,
                )
                if "image" in request.FILES:
                    post.image = request.FILES["image"]
                    post.save()
                messages.success(request, "Пост опубликован!")
                return redirect("community_detail", community_id=community.id)

    return render(
        request,
        "communities/community_detail.html",
        {"community": community, "posts": posts, "is_member": is_member},
    )


@login_required
def join_community(request, community_id):
    """Присоединиться к сообществу"""
    community = get_object_or_404(Community, id=community_id)

    if request.user not in community.members.all():
        community.members.add(request.user)
        messages.success(request, f"Вы присоединились к сообществу {community.name}")
    else:
        messages.info(request, "Вы уже являетесь участником этого сообщества")

    return redirect("community_detail", community_id=community.id)
