from django.db import models
from django.contrib.auth.models import User
from django.db.models import Count, Case, When, IntegerField


class Group(models.Model):
    """Модель группы (сообщества)"""
    THEME_CHOICES = [
        ('music', 'Музыка'),
        ('psychology', 'Психология'),
        ('sport', 'Спорт'),
        ('games', 'Компьютерные игры'),
        ('development', 'Развитие'),
        ('board_games', 'Настольные игры'),
        ('programming', 'Программирование'),
        ('schools', 'Школы'),
        ('design', 'Дизайн'),
        ('other', 'Другое'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='Название сообщества')
    description = models.TextField(max_length=1000, blank=True, verbose_name='Описание')
    theme = models.CharField(max_length=20, choices=THEME_CHOICES, default='other', verbose_name='Тематика')
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_groups', verbose_name='Создатель')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    avatar = models.ImageField(upload_to='groups/avatars/', null=True, blank=True, verbose_name='Аватар')
    
    class Meta:
        ordering = ['-created']
        verbose_name = 'Группа'
        verbose_name_plural = 'Группы'
    
    def __str__(self):
        return self.name
    
    def get_total_rating(self):
        """Получить общий рейтинг группы (положительные - отрицательные)"""
        # Оптимизированный запрос с использованием агрегации
        ratings = GroupRating.objects.filter(group=self).aggregate(
            positive=Count(Case(When(rating=True, then=1), output_field=IntegerField())),
            negative=Count(Case(When(rating=False, then=1), output_field=IntegerField()))
        )
        return (ratings.get('positive', 0) or 0) - (ratings.get('negative', 0) or 0)
    
    def get_rating_count(self):
        """Получить количество оценок"""
        return GroupRating.objects.filter(group=self).count()
    
    def get_subscribers_count(self):
        """Получить количество подписчиков"""
        return GroupSubscription.objects.filter(group=self, is_subscribed=True).count()
    
    def is_owner(self, user):
        """Проверить, является ли пользователь владельцем группы"""
        return self.creator == user
    
    def is_editor(self, user):
        """Проверить, является ли пользователь редактором группы"""
        return GroupMember.objects.filter(
            group=self,
            user=user,
            role__in=['owner', 'editor']
        ).exists()
    
    def can_post(self, user):
        """Проверить, может ли пользователь публиковать посты"""
        return self.is_editor(user) or GroupMember.objects.filter(
            group=self,
            user=user,
            role='member'
        ).exists()
    
    def is_member(self, user):
        """Проверить, является ли пользователь членом группы"""
        return GroupMember.objects.filter(group=self, user=user).exists()
    
    def is_subscribed(self, user):
        """Проверить, подписан ли пользователь на группу"""
        return GroupSubscription.objects.filter(
            group=self,
            user=user,
            is_subscribed=True
        ).exists()


class GroupMember(models.Model):
    """Модель участника группы"""
    ROLE_CHOICES = [
        ('owner', 'Владелец'),
        ('editor', 'Редактор'),
        ('member', 'Участник'),
    ]
    
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='members', verbose_name='Группа')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_memberships', verbose_name='Пользователь')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member', verbose_name='Роль')
    joined = models.DateTimeField(auto_now_add=True, verbose_name='Дата вступления')
    
    class Meta:
        unique_together = ('group', 'user')
        verbose_name = 'Участник группы'
        verbose_name_plural = 'Участники групп'
    
    def __str__(self):
        return f"{self.user.username} - {self.group.name} ({self.role})"
    
    def save(self, *args, **kwargs):
        # Автоматически устанавливаем роль owner для создателя группы
        if not self.pk and self.group.creator == self.user:
            self.role = 'owner'
        super().save(*args, **kwargs)


class GroupPost(models.Model):
    """Модель поста в группе"""
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='posts', verbose_name='Группа')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_posts', verbose_name='Автор')
    content = models.TextField(verbose_name='Содержание')
    image = models.ImageField(upload_to='groups/posts/images/', null=True, blank=True, verbose_name='Изображение')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    
    def get_likes_count(self):
        """Получить количество лайков"""
        return GroupPostLike.objects.filter(post=self).count()
    
    def get_comments_count(self):
        """Получить количество комментариев"""
        return GroupPostComment.objects.filter(post=self).count()
    
    def get_total_engagement(self):
        """Получить общую активность (лайки + комментарии)"""
        return self.get_likes_count() + self.get_comments_count()
    
    def is_liked_by(self, user):
        """Проверить, лайкнул ли пользователь пост"""
        if not user.is_authenticated:
            return False
        return GroupPostLike.objects.filter(post=self, user=user).exists()
    
    class Meta:
        ordering = ['-created']
        verbose_name = 'Пост группы'
        verbose_name_plural = 'Посты групп'
    
    def __str__(self):
        return f'Post in {self.group.name} by {self.author.username}'
    
    def can_delete(self, user):
        """Проверяет, может ли пользователь удалить пост"""
        return self.author == user or self.group.is_editor(user)


class GroupRating(models.Model):
    """Модель рейтинга группы (положительный/отрицательный)"""
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='ratings', verbose_name='Группа')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_ratings', verbose_name='Пользователь')
    rating = models.BooleanField(verbose_name='Рейтинг', help_text='True = положительный, False = отрицательный')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Дата оценки')
    
    class Meta:
        unique_together = ('group', 'user')
        verbose_name = 'Рейтинг группы'
        verbose_name_plural = 'Рейтинги групп'
    
    def __str__(self):
        rating_text = "👍" if self.rating else "👎"
        return f"{self.user.username} {rating_text} {self.group.name}"


class GroupSubscription(models.Model):
    """Модель подписки на группу"""
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='subscriptions', verbose_name='Группа')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_subscriptions', verbose_name='Пользователь')
    is_subscribed = models.BooleanField(default=True, verbose_name='Подписан')
    subscribed_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата подписки')
    
    class Meta:
        unique_together = ('group', 'user')
        verbose_name = 'Подписка на группу'
        verbose_name_plural = 'Подписки на группы'
    
    def __str__(self):
        status = "подписан" if self.is_subscribed else "не подписан"
        return f"{self.user.username} {status} на {self.group.name}"


class GroupPostLike(models.Model):
    """Модель лайка поста группы"""
    post = models.ForeignKey(GroupPost, on_delete=models.CASCADE, related_name='likes', verbose_name='Пост')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_post_likes', verbose_name='Пользователь')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Дата лайка')
    
    class Meta:
        unique_together = ('post', 'user')
        verbose_name = 'Лайк поста группы'
        verbose_name_plural = 'Лайки постов групп'
    
    def __str__(self):
        return f"{self.user.username} лайкнул пост группы {self.post.id}"


class GroupPostComment(models.Model):
    """Модель комментария к посту группы"""
    post = models.ForeignKey(GroupPost, on_delete=models.CASCADE, related_name='comments', verbose_name='Пост')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_post_comments', verbose_name='Автор')
    content = models.TextField(verbose_name='Содержание')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    
    class Meta:
        ordering = ['created']
        verbose_name = 'Комментарий к посту группы'
        verbose_name_plural = 'Комментарии к постам групп'
    
    def __str__(self):
        return f'Comment by {self.author.username} on group post {self.post.id}'
    
    def can_delete(self, user):
        """Проверяет, может ли пользователь удалить комментарий"""
        return self.author == user
    
    def get_likes_count(self):
        """Получить количество лайков"""
        return GroupPostCommentLike.objects.filter(comment=self).count()
    
    def is_liked_by(self, user):
        """Проверить, лайкнул ли пользователь комментарий"""
        if not user.is_authenticated:
            return False
        return GroupPostCommentLike.objects.filter(comment=self, user=user).exists()


class GroupPostCommentLike(models.Model):
    """Модель лайка комментария к посту группы"""
    comment = models.ForeignKey(GroupPostComment, on_delete=models.CASCADE, related_name='likes', verbose_name='Комментарий')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_post_comment_likes', verbose_name='Пользователь')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Дата лайка')
    
    class Meta:
        unique_together = ('comment', 'user')
        verbose_name = 'Лайк комментария группы'
        verbose_name_plural = 'Лайки комментариев групп'
    
    def __str__(self):
        return f"{self.user.username} лайкнул комментарий группы {self.comment.id}"