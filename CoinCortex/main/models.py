from django.db import models
from django.db.models import Avg
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.utils import timezone


class Community(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Название")
    description = models.TextField(verbose_name="Описание")
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_communities', verbose_name="Создатель")
    members = models.ManyToManyField(User, related_name='joined_communities', blank=True, verbose_name="Участники")
    avatar = models.ImageField(upload_to='communities/', null=True, blank=True, verbose_name="Аватар")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    
    class Meta:
        verbose_name = "Сообщество"
        verbose_name_plural = "Сообщества"
    
    def __str__(self):
        return self.name

class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField()
    image = models.ImageField(upload_to='posts/images/', null=True, blank=True, verbose_name='Изображение')
    created = models.DateTimeField(auto_now_add=True)
    wall_owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wall_posts')
    community = models.ForeignKey(Community, on_delete=models.CASCADE, null=True, blank=True, related_name='posts', verbose_name="Сообщество")
    
    class Meta:
        verbose_name = "Пост"
        verbose_name_plural = "Посты"
        ordering = ['-created']
    
    def __str__(self):
        return f'Post by {self.author} at {self.created}'
    
    def can_delete(self, user):
        """Проверяет, может ли пользователь удалить пост"""
        return self.author == user
    
    def get_likes_count(self):
        """Получить количество лайков"""
        return PostLike.objects.filter(post=self).count()
    
    def get_comments_count(self):
        """Получить количество комментариев"""
        return PostComment.objects.filter(post=self).count()
    
    def get_total_engagement(self):
        """Получить общую активность (лайки + комментарии)"""
        return self.get_likes_count() + self.get_comments_count()
    
    def is_liked_by(self, user):
        """Проверить, лайкнул ли пользователь пост"""
        if not user.is_authenticated:
            return False
        return PostLike.objects.filter(post=self, user=user).exists()


class PostLike(models.Model):
    """Модель лайка поста"""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes', verbose_name='Пост')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_likes', verbose_name='Пользователь')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Дата лайка')
    
    class Meta:
        unique_together = ('post', 'user')
        verbose_name = 'Лайк поста'
        verbose_name_plural = 'Лайки постов'
    
    def __str__(self):
        return f"{self.user.username} лайкнул пост {self.post.id}"


class PostComment(models.Model):
    """Модель комментария к посту"""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments', verbose_name='Пост')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_comments', verbose_name='Автор')
    content = models.TextField(verbose_name='Содержание')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    
    class Meta:
        ordering = ['created']
        verbose_name = 'Комментарий к посту'
        verbose_name_plural = 'Комментарии к постам'
    
    def __str__(self):
        return f'Comment by {self.author.username} on post {self.post.id}'
    
    def can_delete(self, user):
        """Проверяет, может ли пользователь удалить комментарий"""
        return self.author == user

# UserRating удален - рейтинг друзьям больше не нужен

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True, verbose_name='Описание профиля')
    first_name = models.CharField(max_length=100, blank=True, verbose_name='Имя')
    last_name = models.CharField(max_length=100, blank=True, verbose_name='Фамилия')
    birth_date = models.DateField(null=True, blank=True, verbose_name='Дата рождения')

    def __str__(self):
        return f'Profile of {self.user.username}'
    
    def get_full_name(self):
        """Получить полное имя"""
        if self.first_name or self.last_name:
            return f"{self.first_name or ''} {self.last_name or ''}".strip()
        return self.user.username

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.profile.save()
    except Profile.DoesNotExist:
        Profile.objects.create(user=instance)

class Friendship(models.Model):
    from_user = models.ForeignKey(User, related_name='friendship_requests_sent', on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name='friendship_requests_received', on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('from_user', 'to_user')
    
    def __str__(self):
        return f"{self.from_user} -> {self.to_user} ({'accepted' if self.accepted else 'pending'})"

# Добавь этот метод в модель User для удобства
def get_friends(self):
    """Получить всех принятых друзей пользователя"""
    sent = User.objects.filter(
        friendship_requests_received__from_user=self,
        friendship_requests_received__accepted=True
    )
    received = User.objects.filter(
        friendship_requests_sent__to_user=self,
        friendship_requests_sent__accepted=True
    )
    return sent.union(received)

User.add_to_class('get_friends', get_friends)


class Chat(models.Model):
    """Модель чата между двумя пользователями"""
    participants = models.ManyToManyField(User, related_name='chats')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated']
    
    def __str__(self):
        return f"Chat {self.id}"
    
    def get_other_participant(self, user):
        """Получить второго участника чата"""
        return self.participants.exclude(id=user.id).first()
    
    def get_last_message(self):
        """Получить последнее сообщение в чате"""
        return self.messages.order_by('-created').first()

class Message(models.Model):
    """Модель сообщения в чате"""
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created']
    
    def __str__(self):
        return f"Message from {self.sender} in chat {self.chat.id}"

# Добавляем метод к User для удобства
def get_or_create_chat(self, other_user):
    """Получить или создать чат с другим пользователем"""
    chat = Chat.objects.filter(participants=self).filter(participants=other_user).first()
    if not chat:
        chat = Chat.objects.create()
        chat.participants.add(self, other_user)
    return chat

User.add_to_class('get_or_create_chat', get_or_create_chat)