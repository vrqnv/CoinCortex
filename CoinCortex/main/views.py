from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from .models import (
    Post,
    PostLike,
    PostComment,
    PostCommentLike,
    Friendship,
    Chat,
    Message,
    Notification,
    Community,
)
from .forms import CustomUserCreationForm


def index(request):
    """Главная страница с лентой постов от популярных групп"""
    # Обработка POST запросов (лайки и комментарии)
    if request.method == "POST" and request.user.is_authenticated:
        # Лайк поста
        if "like_post" in request.POST:
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
                        is_liked = False
                    else:
                        is_liked = True
                        if post.author != request.user:
                            Notification.objects.create(
                                user=post.author,
                                notification_type="group_like",
                                from_user=request.user,
                                group_post=post,
                            )
                    likes_count = post.get_likes_count()
                else:
                    # Лайк обычного поста
                    post = Post.objects.get(id=post_id)
                    like, created = PostLike.objects.get_or_create(
                        post=post, user=request.user
                    )
                    if not created:
                        like.delete()
                        is_liked = False
                    else:
                        is_liked = True
                        if post.author != request.user:
                            Notification.objects.create(
                                user=post.author,
                                notification_type="like",
                                from_user=request.user,
                                post=post,
                            )
                    likes_count = post.get_likes_count()
                
                # Если это AJAX запрос, возвращаем JSON
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    from django.http import JsonResponse
                    return JsonResponse({
                        'success': True,
                        'is_liked': is_liked,
                        'likes_count': likes_count
                    })
            except (Post.DoesNotExist, Exception):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    from django.http import JsonResponse
                    return JsonResponse({'success': False, 'error': 'Пост не найден'}, status=404)
                messages.error(request, "Пост не найден")
            return redirect("index")

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
                    else:
                        # Комментарий к обычному посту
                        post = Post.objects.get(id=post_id)
                        comment = PostComment.objects.create(
                            post=post, author=request.user, content=comment_text
                        )
                        if post.author != request.user:
                            Notification.objects.create(
                                user=post.author,
                                notification_type="comment",
                                from_user=request.user,
                                post=post,
                            )
                except (Post.DoesNotExist, Exception):
                    messages.error(request, "Пост не найден")
            return redirect("index")

        # Лайк комментария
        elif "like_comment" in request.POST:
            comment_id = request.POST.get("like_comment")
            try:
                if comment_id.startswith("group_"):
                    # Лайк комментария группы
                    from groups.models import GroupPostComment, GroupPostCommentLike

                    comment_id = comment_id.replace("group_", "")
                    comment = GroupPostComment.objects.get(id=comment_id)
                    like, created = GroupPostCommentLike.objects.get_or_create(
                        comment=comment, user=request.user
                    )
                    if not created:
                        like.delete()
                    else:
                        if comment.author != request.user:
                            Notification.objects.create(
                                user=comment.author,
                                notification_type="group_comment_like",
                                from_user=request.user,
                                group_comment=comment,
                            )
                else:
                    # Лайк обычного комментария
                    comment = PostComment.objects.get(id=comment_id)
                    like, created = PostCommentLike.objects.get_or_create(
                        comment=comment, user=request.user
                    )
                    if not created:
                        like.delete()
                    else:
                        if comment.author != request.user:
                            Notification.objects.create(
                                user=comment.author,
                                notification_type="comment_like",
                                from_user=request.user,
                                comment=comment,
                            )
            except (PostComment.DoesNotExist, Exception):
                messages.error(request, "Комментарий не найден")
            return redirect("index")

    # Получаем посты для авторизованных пользователей
    all_posts = []

    if request.user.is_authenticated:
        from groups.models import Group, GroupPost, GroupSubscription

        # Получаем друзей пользователя
        sent_friends = User.objects.filter(
            friendship_requests_received__from_user=request.user,
            friendship_requests_received__accepted=True,
        )
        received_friends = User.objects.filter(
            friendship_requests_sent__to_user=request.user,
            friendship_requests_sent__accepted=True,
        )
        friends_list = list(sent_friends.union(received_friends))
        friends_ids = [f.id for f in friends_list]

        # Получаем ID сообществ, на которые подписан пользователь
        subscribed_groups = GroupSubscription.objects.filter(
            user=request.user, is_subscribed=True
        ).values_list("group_id", flat=True)

        # Получаем посты от друзей и свои посты
        friends_posts = (
            Post.objects.filter(
                Q(author__in=friends_ids) | Q(wall_owner__in=friends_ids) | Q(author=request.user)
            )
            .select_related("author", "wall_owner")
            .order_by("-created")
        )

        # Получаем посты из подписанных сообществ
        group_posts = (
            GroupPost.objects.filter(group_id__in=subscribed_groups)
            .select_related("group", "author")
            .order_by("-created")
        )

        # Добавляем посты друзей
        for post in friends_posts:
            is_liked = post.is_liked_by(request.user)
            comments = post.comments.select_related("author").all()
            # Добавляем информацию о лайках для каждого комментария
            comments_with_likes = []
            for comment in comments[:5]:
                comments_with_likes.append({
                    'comment': comment,
                    'is_liked': comment.is_liked_by(request.user),
                    'likes_count': comment.get_likes_count(),
                })
            # Самый популярный комментарий (первый по дате, если нет лайков)
            top_comment = comments.first() if comments.exists() else None
            all_posts.append(
                {
                    "post": post,
                    "type": "user",
                    "is_liked": is_liked,
                    "likes_count": post.get_likes_count(),
                    "comments_count": post.get_comments_count(),
                    "comments": comments_with_likes,
                    "top_comment": top_comment,
                }
            )

        # Добавляем посты из групп
        for post in group_posts:
            is_liked = post.is_liked_by(request.user)
            comments = post.comments.select_related("author").all()
            # Добавляем информацию о лайках для каждого комментария
            comments_with_likes = []
            for comment in comments[:5]:
                comments_with_likes.append({
                    'comment': comment,
                    'is_liked': comment.is_liked_by(request.user),
                    'likes_count': comment.get_likes_count(),
                })
            # Самый популярный комментарий (первый по дате, если нет лайков)
            top_comment = comments.first() if comments.exists() else None
            all_posts.append(
                {
                    "post": post,
                    "type": "group",
                    "is_liked": is_liked,
                    "likes_count": post.get_likes_count(),
                    "comments_count": post.get_comments_count(),
                    "comments": comments_with_likes,
                    "top_comment": top_comment,
                }
            )
    else:
        # Для неавторизованных - показываем посты из популярных групп
        from groups.models import Group, GroupPost

        popular_groups = (
            Group.objects.annotate(
                subscribers_count=Count(
                    "subscriptions", filter=Q(subscriptions__is_subscribed=True)
                )
            )
            .filter(subscribers_count__gt=0)
            .order_by("-subscribers_count", "-created")[:10]
        )

        group_posts = (
            GroupPost.objects.filter(group__in=popular_groups)
            .select_related("group", "author")
            .order_by("-created")
        )

        for post in group_posts:
            comments = post.comments.select_related("author").all()
            top_comment = comments.first() if comments.exists() else None
            all_posts.append(
                {
                    "post": post,
                    "type": "group",
                    "is_liked": False,
                    "likes_count": post.get_likes_count(),
                    "comments_count": post.get_comments_count(),
                    "comments": comments[:5],
                    "top_comment": top_comment,
                }
            )

    # Сортируем по дате создания (новые сначала)
    all_posts.sort(key=lambda x: x["post"].created, reverse=True)
    all_posts = all_posts[:50]

    # Получаем количество непрочитанных уведомлений
    unread_notifications = 0
    if request.user.is_authenticated:
        unread_notifications = Notification.objects.filter(
            user=request.user, read=False
        ).count()

    return render(
        request,
        "index.html",
        {
            "all_posts": all_posts,
            "unread_notifications": unread_notifications,
        },
    )


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
                return redirect("profile")

        # Удаление поста
        elif "delete_post" in request.POST:
            post_id = request.POST.get("delete_post")
            try:
                post = Post.objects.get(id=post_id, author=request.user)
                post.delete()
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
                        if not existing_friendship.accepted:
                            if existing_friendship.from_user != request.user:
                                # Принимаем входящую заявку
                                existing_friendship.accepted = True
                                existing_friendship.save()
                    else:
                        friendship = Friendship.objects.create(
                            from_user=request.user, to_user=friend_user, accepted=False
                        )
                        # Создаем уведомление о заявке в друзья
                        Notification.objects.create(
                            user=friend_user,
                            notification_type="friend_request",
                            from_user=request.user,
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
                # Создаем уведомление о принятии заявки
                Notification.objects.create(
                    user=friendship.from_user,
                    notification_type="friend_accepted",
                    from_user=request.user,
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
                    else:
                        if post.author != request.user:
                            Notification.objects.create(
                                user=post.author,
                                notification_type="group_like",
                                from_user=request.user,
                                group_post=post,
                            )
                else:
                    # Лайк обычного поста
                    post = Post.objects.get(id=post_id)
                    like, created = PostLike.objects.get_or_create(
                        post=post, user=request.user
                    )
                    if not created:
                        like.delete()
                    else:
                        if post.author != request.user:
                            Notification.objects.create(
                                user=post.author,
                                notification_type="like",
                                from_user=request.user,
                                post=post,
                            )
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
                    else:
                        # Комментарий к обычному посту
                        post = Post.objects.get(id=post_id)
                        comment = PostComment.objects.create(
                            post=post, author=request.user, content=comment_text
                        )
                        if post.author != request.user:
                            Notification.objects.create(
                                user=post.author,
                                notification_type="comment",
                                from_user=request.user,
                                post=post,
                            )
                except (Post.DoesNotExist, GroupPost.DoesNotExist):
                    messages.error(request, "Пост не найден")
            referer = request.META.get("HTTP_REFERER", "index")
            return redirect(referer)

        # Лайк комментария
        elif "like_comment" in request.POST:
            comment_id = request.POST.get("like_comment")
            try:
                if comment_id.startswith("group_"):
                    # Лайк комментария группы
                    from groups.models import GroupPostComment, GroupPostCommentLike

                    comment_id = comment_id.replace("group_", "")
                    comment = GroupPostComment.objects.get(id=comment_id)
                    like, created = GroupPostCommentLike.objects.get_or_create(
                        comment=comment, user=request.user
                    )
                    if not created:
                        like.delete()
                    else:
                        if comment.author != request.user:
                            Notification.objects.create(
                                user=comment.author,
                                notification_type="group_comment_like",
                                from_user=request.user,
                                group_comment=comment,
                            )
                else:
                    # Лайк обычного комментария
                    comment = PostComment.objects.get(id=comment_id)
                    like, created = PostCommentLike.objects.get_or_create(
                        comment=comment, user=request.user
                    )
                    if not created:
                        like.delete()
                    else:
                        if comment.author != request.user:
                            Notification.objects.create(
                                user=comment.author,
                                notification_type="comment_like",
                                from_user=request.user,
                                comment=comment,
                            )
            except (PostComment.DoesNotExist, Exception):
                messages.error(request, "Комментарий не найден")
            referer = request.META.get("HTTP_REFERER", "index")
            return redirect(referer)

        # Лайк комментария
        elif "like_comment" in request.POST:
            comment_id = request.POST.get("like_comment")
            try:
                if comment_id.startswith("group_"):
                    # Лайк комментария группы
                    from groups.models import GroupPostComment, GroupPostCommentLike

                    comment_id = comment_id.replace("group_", "")
                    comment = GroupPostComment.objects.get(id=comment_id)
                    like, created = GroupPostCommentLike.objects.get_or_create(
                        comment=comment, user=request.user
                    )
                    if not created:
                        like.delete()
                    else:
                        if comment.author != request.user:
                            Notification.objects.create(
                                user=comment.author,
                                notification_type="group_comment_like",
                                from_user=request.user,
                                group_comment=comment,
                            )
                else:
                    # Лайк обычного комментария
                    comment = PostComment.objects.get(id=comment_id)
                    like, created = PostCommentLike.objects.get_or_create(
                        comment=comment, user=request.user
                    )
                    if not created:
                        like.delete()
                    else:
                        if comment.author != request.user:
                            Notification.objects.create(
                                user=comment.author,
                                notification_type="comment_like",
                                from_user=request.user,
                                comment=comment,
                            )
            except (PostComment.DoesNotExist, Exception):
                messages.error(request, "Комментарий не найден")
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
        comments = post.comments.select_related("author").all()[:5]
        comments_with_likes = []
        for comment in comments:
            comments_with_likes.append({
                'comment': comment,
                'is_liked': comment.is_liked_by(request.user),
                'likes_count': comment.get_likes_count(),
            })
        posts_with_info.append(
            {
                "post": post,
                "is_liked": post.is_liked_by(request.user),
                "likes_count": post.get_likes_count(),
                "comments_count": post.get_comments_count(),
                "comments": comments_with_likes,
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

    # Получаем сообщества, на которые подписан пользователь
    from groups.models import Group, GroupSubscription
    user_communities = Group.objects.filter(
        subscriptions__user=request.user,
        subscriptions__is_subscribed=True
    ).select_related().distinct().order_by('-created')[:20]

    return render(
        request,
        "profile.html",
        {
            "user": request.user,
            "posts": posts_with_info,
            "user_communities": user_communities,
        },
    )


def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
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

        # Обработка POST запросов
        if request.method == "POST":
            # Создание поста на стене друга
            if "content" in request.POST:
                content = request.POST.get("content", "").strip()
                if content:
                    post = Post.objects.create(
                        author=request.user,
                        content=content,
                        wall_owner=profile_user,  # Пост на стене друга
                    )
                    if "image" in request.FILES:
                        post.image = request.FILES["image"]
                        post.save()
                    return redirect("user_profile", username=username)

            # Лайк поста
            elif "like_post" in request.POST:
                post_id = request.POST.get("like_post")
                try:
                    post = Post.objects.get(id=post_id)
                    like, created = PostLike.objects.get_or_create(
                        post=post, user=request.user
                    )
                    if not created:
                        like.delete()
                    else:
                        if post.author != request.user:
                            Notification.objects.create(
                                user=post.author,
                                notification_type="like",
                                from_user=request.user,
                                post=post,
                            )
                except Post.DoesNotExist:
                    messages.error(request, "Пост не найден")
                return redirect("user_profile", username=username)

            # Комментарий к посту
            elif "comment_post" in request.POST:
                post_id = request.POST.get("comment_post")
                comment_text = request.POST.get("comment_text", "").strip()
                if comment_text:
                    try:
                        post = Post.objects.get(id=post_id)
                        comment = PostComment.objects.create(
                            post=post, author=request.user, content=comment_text
                        )
                        if post.author != request.user:
                            Notification.objects.create(
                                user=post.author,
                                notification_type="comment",
                                from_user=request.user,
                                post=post,
                            )
                    except Post.DoesNotExist:
                        messages.error(request, "Пост не найден")
                return redirect("user_profile", username=username)

        # Проверяем, является ли пользователь другом
        is_friend = Friendship.objects.filter(
            (
                Q(from_user=request.user, to_user=profile_user)
                | Q(from_user=profile_user, to_user=request.user)
            ),
            accepted=True,
        ).exists()

        # Получаем посты на стене пользователя (все посты, где wall_owner = profile_user)
        user_posts = (
            Post.objects.filter(wall_owner=profile_user)
            .select_related("author", "wall_owner")
            .order_by("-created")[:20]
        )

        # Добавляем информацию о лайках и комментариях
        posts_with_info = []
        for post in user_posts:
            comments = post.comments.select_related("author").all()[:5]
            comments_with_likes = []
            for comment in comments:
                comments_with_likes.append({
                    'comment': comment,
                    'is_liked': comment.is_liked_by(request.user),
                    'likes_count': comment.get_likes_count(),
                })
            posts_with_info.append(
                {
                    "post": post,
                    "is_liked": post.is_liked_by(request.user),
                    "likes_count": post.get_likes_count(),
                    "comments_count": post.get_comments_count(),
                    "comments": comments_with_likes,
                }
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
            "posts": posts_with_info,
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

    # Поиск друзей для нового чата (по имени, фамилии и нику)
    search_query = request.GET.get("search", "").strip()
    search_results = []
    if search_query:
        # Ищем среди друзей - преобразуем union в список перед фильтрацией
        sent_friends = User.objects.filter(
            friendship_requests_received__from_user=request.user,
            friendship_requests_received__accepted=True,
        )
        received_friends = User.objects.filter(
            friendship_requests_sent__to_user=request.user,
            friendship_requests_sent__accepted=True,
        )
        friends_list = list(sent_friends.union(received_friends))
        friends_ids = [f.id for f in friends_list]
        
        # Теперь фильтруем по поисковому запросу (по имени, фамилии и нику)
        search_results = User.objects.filter(
            id__in=friends_ids
        ).filter(
            Q(username__icontains=search_query) |
            Q(profile__first_name__icontains=search_query) |
            Q(profile__last_name__icontains=search_query)
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
    """Начать новый чат с пользователем по нику"""
    try:
        # Ищем пользователя по нику (точное совпадение или частичное)
        other_user = User.objects.filter(username__iexact=username).first()
        if not other_user:
            # Если точного совпадения нет, ищем частичное
            other_user = User.objects.filter(username__icontains=username).first()

        if not other_user:
            messages.error(request, f"Пользователь '{username}' не найден")
            return redirect("chat")

        if other_user == request.user:
            messages.error(request, "Нельзя начать чат с собой")
            return redirect("chat")

        # Получаем или создаем чат
        chat = request.user.get_or_create_chat(other_user)
        return redirect("chat_detail", chat_id=chat.id)

    except Exception as e:
        messages.error(request, f"Ошибка при создании чата: {str(e)}")
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
        return redirect("profile")

    return render(request, "registration/edit_profile.html", {"profile": profile})


@login_required
def delete_account(request):
    """Удаление аккаунта"""
    if request.method == "POST":
        if "confirm" in request.POST:
            request.user.delete()
            return redirect("index")

    return render(request, "registration/delete_account.html")


@login_required
def friends_page(request):
    """Страница со списком друзей"""
    # Обработка POST запросов
    if request.method == "POST":
        # Добавление в друзья
        if "add_friend" in request.POST:
            username = request.POST.get("add_friend")
            try:
                friend_user = User.objects.get(username=username)
                if friend_user == request.user:
                    messages.error(request, "Нельзя добавить себя в друзья")
                else:
                    existing_friendship = Friendship.objects.filter(
                        Q(from_user=request.user, to_user=friend_user)
                        | Q(from_user=friend_user, to_user=request.user)
                    ).first()

                    if existing_friendship:
                        if not existing_friendship.accepted:
                            if existing_friendship.from_user != request.user:
                                existing_friendship.accepted = True
                                existing_friendship.save()
                    else:
                        friendship = Friendship.objects.create(
                            from_user=request.user, to_user=friend_user, accepted=False
                        )
                        # Создаем уведомление о заявке в друзья
                        Notification.objects.create(
                            user=friend_user,
                            notification_type="friend_request",
                            from_user=request.user,
                        )
            except User.DoesNotExist:
                messages.error(request, "Пользователь не найден")
            return redirect("friends")

        # Принятие заявки
        elif "accept_friend" in request.POST:
            friend_id = request.POST.get("accept_friend")
            try:
                friendship = Friendship.objects.get(
                    id=friend_id, to_user=request.user, accepted=False
                )
                friendship.accepted = True
                friendship.save()
                # Создаем уведомление о принятии заявки
                Notification.objects.create(
                    user=friendship.from_user,
                    notification_type="friend_accepted",
                    from_user=request.user,
                )
            except Friendship.DoesNotExist:
                messages.error(request, "Заявка не найдена")
            return redirect("friends")

        # Удаление друга
        elif "remove_friend" in request.POST:
            username = request.POST.get("remove_friend")
            try:
                friend_user = User.objects.get(username=username)
                Friendship.objects.filter(
                    Q(from_user=request.user, to_user=friend_user)
                    | Q(from_user=friend_user, to_user=request.user),
                    accepted=True,
                ).delete()
            except User.DoesNotExist:
                messages.error(request, "Пользователь не найден")
            return redirect("friends")

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
    friends_ids = [f.id for f in friends_list]

    # Получаем входящие заявки
    incoming_requests = Friendship.objects.filter(
        to_user=request.user, accepted=False
    ).select_related("from_user")

    # Получаем исходящие заявки
    outgoing_requests = Friendship.objects.filter(
        from_user=request.user, accepted=False
    ).select_related("to_user")

    # Получаем ID всех пользователей с заявками
    pending_ids = set()
    for req in incoming_requests:
        pending_ids.add(req.from_user.id)
    for req in outgoing_requests:
        pending_ids.add(req.to_user.id)

    # Получаем возможных друзей на основе общих сообществ
    from groups.models import GroupSubscription, Group

    # Получаем ID сообществ, на которые подписан текущий пользователь
    user_subscribed_groups = GroupSubscription.objects.filter(
        user=request.user, is_subscribed=True
    ).values_list("group_id", flat=True)

    possible_friends = []
    if user_subscribed_groups:
        # Получаем пользователей, которые подписаны на те же сообщества
        recommended_users = (
            User.objects.filter(
                group_subscriptions__group_id__in=user_subscribed_groups,
                group_subscriptions__is_subscribed=True,
            )
            .exclude(id=request.user.id)
            .exclude(id__in=friends_ids)
            .exclude(id__in=pending_ids)
            .annotate(
                common_groups_count=Count(
                    "group_subscriptions",
                    filter=Q(
                        group_subscriptions__group_id__in=user_subscribed_groups,
                        group_subscriptions__is_subscribed=True,
                    ),
                )
            )
            .filter(common_groups_count__gt=0)
            .select_related("profile")
            .order_by("-common_groups_count", "-date_joined")[:20]
        )

        # Преобразуем в список с информацией о количестве общих сообществ и их названиях
        for user in recommended_users:
            # Получаем общие сообщества
            user_groups = GroupSubscription.objects.filter(
                user=user, is_subscribed=True, group_id__in=user_subscribed_groups
            ).values_list("group_id", flat=True)
            common_groups = Group.objects.filter(id__in=user_groups)

            possible_friends.append(
                {
                    "user": user,
                    "common_groups_count": user.common_groups_count,
                    "common_groups": common_groups,
                }
            )

    # Поиск пользователей (по имени, фамилии и нику)
    search_query = request.GET.get("search", "").strip()
    search_results = []
    if search_query:
        search_results = (
            User.objects.filter(
                Q(username__icontains=search_query) |
                Q(profile__first_name__icontains=search_query) |
                Q(profile__last_name__icontains=search_query)
            )
            .exclude(id=request.user.id)
            .distinct()
            .select_related("profile")[:10]
        )

    # Получаем количество непрочитанных уведомлений
    unread_notifications = Notification.objects.filter(
        user=request.user, read=False
    ).count()

    return render(
        request,
        "friends.html",
        {
            "friends": friends_list,
            "incoming_requests": incoming_requests,
            "outgoing_requests": outgoing_requests,
            "possible_friends": possible_friends,
            "search_results": search_results,
            "search_query": search_query,
            "unread_notifications": unread_notifications,
        },
    )


@login_required
def notifications(request):
    """Страница уведомлений"""
    user_notifications = (
        Notification.objects.filter(user=request.user)
        .select_related("from_user", "post", "group_post")
        .prefetch_related("from_user__friendship_requests_sent")
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

    return redirect("community_detail", community_id=community.id)
