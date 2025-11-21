from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save

class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    wall_owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wall_posts')
    
    class Meta:
        ordering = ['-created']
    
    def __str__(self):
        return f'Post by {self.author} at {self.created}'
    
    def can_delete(self, user):
        """Проверяет, может ли пользователь удалить пост"""
        return self.author == user

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)

    def __str__(self):
        return f'Profile of {self.user.username}'

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