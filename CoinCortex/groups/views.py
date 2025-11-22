from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, F
from django.core.paginator import Paginator
from .models import Group, GroupPost, GroupMember, GroupRating, GroupSubscription, GroupPostLike, GroupPostComment, GroupPostCommentLike
from main.models import Notification
from django.contrib.auth.models import User


@login_required
def groups_list(request):
    """Список всех сообществ"""
    search_query = request.GET.get('search', '').strip()
    theme_filter = request.GET.get('theme', '')
    sort_by = request.GET.get('sort', 'created')  # created, rating
    
    groups = Group.objects.annotate(
        subscribers_count=Count('subscriptions', filter=Q(subscriptions__is_subscribed=True)),
        rating_positive=Count('ratings', filter=Q(ratings__rating=True)),
        rating_negative=Count('ratings', filter=Q(ratings__rating=False)),
        total_rating=F('rating_positive') - F('rating_negative')
    )
    
    # Фильтрация по тематике
    if theme_filter:
        groups = groups.filter(theme=theme_filter)
    
    # Поиск
    if search_query:
        groups = groups.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Сортировка
    if sort_by == 'rating':
        groups = groups.order_by('-total_rating', '-created')
    else:
        groups = groups.order_by('-created')
    
    # Добавляем информацию о подписке для каждой группы
    for group in groups:
        group.user_is_subscribed = group.is_subscribed(request.user)
        group.user_is_member = group.is_member(request.user)
        group.user_can_post = group.can_post(request.user)
    
    paginator = Paginator(groups, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'groups/groups_list.html', {
        'groups': page_obj,
        'search_query': search_query,
        'theme_filter': theme_filter,
        'sort_by': sort_by,
        'themes': Group.THEME_CHOICES
    })


@login_required
def group_create(request):
    """Создание нового сообщества"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        theme = request.POST.get('theme', 'other')
        avatar = request.FILES.get('avatar')
        
        if not name:
            messages.error(request, 'Название сообщества обязательно')
            return render(request, 'groups/group_create.html', {
                'themes': Group.THEME_CHOICES
            })
        
        if len(name) > 200:
            messages.error(request, 'Название сообщества слишком длинное (максимум 200 символов)')
            return render(request, 'groups/group_create.html', {
                'themes': Group.THEME_CHOICES
            })
        
        group = Group.objects.create(
            name=name,
            description=description,
            theme=theme,
            creator=request.user
        )
        
        if avatar:
            group.avatar = avatar
            group.save()
        
        # Автоматически добавляем создателя как владельца
        GroupMember.objects.create(
            group=group,
            user=request.user,
            role='owner'
        )
        
        # Автоматически подписываем создателя на сообщество
        GroupSubscription.objects.get_or_create(
            group=group,
            user=request.user,
            defaults={'is_subscribed': True}
        )
        
        return redirect('group_detail', group_id=group.id)
    
    return render(request, 'groups/group_create.html', {
        'themes': Group.THEME_CHOICES
    })


@login_required
def group_detail(request, group_id):
    """Детальная страница группы"""
    group = get_object_or_404(Group, id=group_id)
    
    # Обработка POST запросов
    if request.method == 'POST':
        # Подписка/отписка
        if 'toggle_subscription' in request.POST:
            subscription, created = GroupSubscription.objects.get_or_create(
                group=group,
                user=request.user,
                defaults={'is_subscribed': True}
            )
            if not created:
                subscription.is_subscribed = not subscription.is_subscribed
                subscription.save()
            
            return redirect('group_detail', group_id=group.id)
        
        # Создание поста
        elif 'create_post' in request.POST:
            content = request.POST.get('content', '').strip()
            image = request.FILES.get('image')
            if not content:
                messages.error(request, 'Содержание поста не может быть пустым')
            elif not group.can_post(request.user):
                messages.error(request, 'У вас нет прав для публикации постов в этой группе')
            else:
                post = GroupPost.objects.create(
                    group=group,
                    author=request.user,
                    content=content
                )
                if image:
                    post.image = image
                    post.save()
            return redirect('group_detail', group_id=group.id)
        
        # Лайк поста группы
        elif 'like_group_post' in request.POST:
            post_id = request.POST.get('like_group_post')
            try:
                post = GroupPost.objects.get(id=post_id, group=group)
                like, created = GroupPostLike.objects.get_or_create(post=post, user=request.user)
                if not created:
                    like.delete()
                else:
                    # Уведомление
                    if post.author != request.user:
                        Notification.objects.create(
                            user=post.author,
                            notification_type='group_like',
                            from_user=request.user,
                            group_post=post
                        )
            except GroupPost.DoesNotExist:
                messages.error(request, 'Пост не найден')
            referer = request.META.get('HTTP_REFERER', 'group_detail')
            if 'group_detail' in referer:
                return redirect('group_detail', group_id=group.id)
            return redirect(referer)
        
        # Комментарий к посту группы
        elif 'comment_group_post' in request.POST:
            post_id = request.POST.get('comment_group_post')
            comment_text = request.POST.get('comment_text', '').strip()
            if comment_text:
                try:
                    post = GroupPost.objects.get(id=post_id, group=group)
                    comment = GroupPostComment.objects.create(
                        post=post,
                        author=request.user,
                        content=comment_text
                    )
                    # Уведомление
                    if post.author != request.user:
                        Notification.objects.create(
                            user=post.author,
                            notification_type='group_comment',
                            from_user=request.user,
                            group_post=post
                        )
                except GroupPost.DoesNotExist:
                    messages.error(request, 'Пост не найден')
            referer = request.META.get('HTTP_REFERER', 'group_detail')
            if 'group_detail' in referer:
                return redirect('group_detail', group_id=group.id)
            return redirect(referer)
        
        # Лайк комментария группы
        elif 'like_group_comment' in request.POST:
            comment_id = request.POST.get('like_group_comment')
            try:
                comment = GroupPostComment.objects.get(id=comment_id, post__group=group)
                like, created = GroupPostCommentLike.objects.get_or_create(comment=comment, user=request.user)
                if not created:
                    like.delete()
                else:
                    # Уведомление
                    if comment.author != request.user:
                        Notification.objects.create(
                            user=comment.author,
                            notification_type='group_comment_like',
                            from_user=request.user,
                            group_comment=comment
                        )
            except GroupPostComment.DoesNotExist:
                messages.error(request, 'Комментарий не найден')
            referer = request.META.get('HTTP_REFERER', 'group_detail')
            if 'group_detail' in referer:
                return redirect('group_detail', group_id=group.id)
            return redirect(referer)
        
        # Удаление поста
        elif 'delete_post' in request.POST:
            post_id = request.POST.get('delete_post')
            try:
                post = GroupPost.objects.get(id=post_id, group=group)
                if post.can_delete(request.user):
                    post.delete()
                else:
                    messages.error(request, 'У вас нет прав для удаления этого поста')
            except GroupPost.DoesNotExist:
                messages.error(request, 'Пост не найден')
            return redirect('group_detail', group_id=group.id)
        
        # Рейтинг группы
        elif 'rate_group' in request.POST:
            rating_value = request.POST.get('rating')
            if rating_value in ['positive', 'negative']:
                rating_bool = (rating_value == 'positive')
                GroupRating.objects.update_or_create(
                    group=group,
                    user=request.user,
                    defaults={'rating': rating_bool}
                )
            return redirect('group_detail', group_id=group.id)
        
        # Добавление редактора
        elif 'add_editor' in request.POST:
            if not group.is_owner(request.user):
                messages.error(request, 'Только владелец группы может добавлять редакторов')
            else:
                username = request.POST.get('add_editor', '').strip()
                try:
                    editor_user = User.objects.get(username=username)
                    if editor_user == request.user:
                        messages.error(request, 'Вы уже владелец группы')
                    else:
                        member, created = GroupMember.objects.get_or_create(
                            group=group,
                            user=editor_user,
                            defaults={'role': 'editor'}
                        )
                        if not created:
                            member.role = 'editor'
                            member.save()
                except User.DoesNotExist:
                    messages.error(request, 'Пользователь не найден')
            return redirect('group_detail', group_id=group.id)
        
        # Удаление редактора
        elif 'remove_editor' in request.POST:
            if not group.is_owner(request.user):
                messages.error(request, 'Только владелец группы может удалять редакторов')
            else:
                user_id = request.POST.get('remove_editor')
                try:
                    member = GroupMember.objects.get(id=user_id, group=group)
                    if member.role == 'owner':
                        messages.error(request, 'Нельзя удалить владельца группы')
                    else:
                        member.delete()
                except GroupMember.DoesNotExist:
                    messages.error(request, 'Участник не найден')
            return redirect('group_detail', group_id=group.id)
        
        # Удаление сообщества
        elif 'delete_group' in request.POST:
            if not group.is_owner(request.user):
                messages.error(request, 'Только владелец группы может удалить сообщество')
            else:
                group_name = group.name
                group.delete()
                return redirect('my_groups')
    
    # Получаем посты группы
    posts = GroupPost.objects.filter(group=group).select_related('author', 'group').order_by('-created')
    
    # Информация о группе
    group.total_rating = group.get_total_rating()
    group.rating_count = group.get_rating_count()
    group.subscribers_count = group.get_subscribers_count()
    group.user_is_subscribed = group.is_subscribed(request.user)
    group.user_is_member = group.is_member(request.user)
    group.user_can_post = group.can_post(request.user)
    group.user_is_owner = group.is_owner(request.user)
    group.user_is_editor = group.is_editor(request.user)
    
    # Получаем текущий рейтинг пользователя
    user_rating = None
    try:
        rating = GroupRating.objects.get(group=group, user=request.user)
        user_rating = 'positive' if rating.rating else 'negative'
    except GroupRating.DoesNotExist:
        pass
    
    # Получаем редакторов группы
    editors = GroupMember.objects.filter(group=group, role__in=['owner', 'editor']).select_related('user')
    
    # Получаем подписчиков группы
    subscribers = User.objects.filter(
        group_subscriptions__group=group,
        group_subscriptions__is_subscribed=True
    ).select_related('profile')[:50]  # Первые 50 подписчиков
    
    # Пагинация постов
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Добавляем информацию о правах удаления, лайках и комментариях для каждого поста
    posts_with_permissions = []
    for post in page_obj:
        comments = post.comments.select_related('author').all()
        # Добавляем информацию о лайках для каждого комментария
        comments_with_likes = []
        for comment in comments[:10]:
            comments_with_likes.append({
                'comment': comment,
                'is_liked': comment.is_liked_by(request.user),
                'likes_count': comment.get_likes_count(),
            })
        # Самый популярный комментарий (первый по дате)
        top_comment = comments.first() if comments.exists() else None
        posts_with_permissions.append({
            'post': post,
            'can_delete': post.can_delete(request.user),
            'is_liked': post.is_liked_by(request.user),
            'likes_count': post.get_likes_count(),
            'comments_count': post.get_comments_count(),
            'comments': comments_with_likes,
            'top_comment': top_comment
        })
    
    return render(request, 'groups/group_detail.html', {
        'group': group,
        'posts': posts_with_permissions,
        'user_rating': user_rating,
        'editors': editors,
        'subscribers': subscribers,
        'page_obj': page_obj  # Для пагинации
    })


@login_required
def my_groups(request):
    """Сообщества пользователя (созданные, редактируемые, подписанные)"""
    # Сообщества, созданные пользователем
    created_groups = Group.objects.filter(creator=request.user).annotate(
        subscribers_count=Count('subscriptions', filter=Q(subscriptions__is_subscribed=True))
    ).order_by('-created')
    
    # Сообщества, где пользователь является редактором
    edited_groups = Group.objects.filter(
        members__user=request.user,
        members__role__in=['owner', 'editor']
    ).exclude(creator=request.user).annotate(
        subscribers_count=Count('subscriptions', filter=Q(subscriptions__is_subscribed=True))
    ).distinct().order_by('-created')
    
    # Сообщества, на которые подписан пользователь
    subscribed_groups = Group.objects.filter(
        subscriptions__user=request.user,
        subscriptions__is_subscribed=True
    ).annotate(
        subscribers_count=Count('subscriptions', filter=Q(subscriptions__is_subscribed=True))
    ).distinct().order_by('-created')
    
    return render(request, 'groups/my_groups.html', {
        'created_groups': created_groups,
        'edited_groups': edited_groups,
        'subscribed_groups': subscribed_groups
    })


@login_required
def group_delete(request, group_id):
    """Удаление сообщества (только для владельца)"""
    group = get_object_or_404(Group, id=group_id)
    
    if not group.is_owner(request.user):
        messages.error(request, 'Только владелец группы может удалить сообщество')
        return redirect('group_detail', group_id=group.id)
    
    if request.method == 'POST':
        group_name = group.name
        group.delete()
        return redirect('my_groups')
    
    return render(request, 'groups/group_delete.html', {
        'group': group
    })


@login_required
def group_subscribers(request, group_id):
    """Просмотр подписчиков сообщества"""
    group = get_object_or_404(Group, id=group_id)
    
    subscribers = User.objects.filter(
        group_subscriptions__group=group,
        group_subscriptions__is_subscribed=True
    ).select_related('profile').order_by('username')
    
    paginator = Paginator(subscribers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'groups/group_subscribers.html', {
        'group': group,
        'subscribers': page_obj
    })
