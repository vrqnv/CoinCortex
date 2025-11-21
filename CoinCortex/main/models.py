from django.db import models
from django.db.models import Avg
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save

class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    wall_owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wall_posts')
    
    def __str__(self):
        return f'Post by {self.author} on {self.created}'

class UserRating(models.Model):
    rated_user = models.ForeignKey(User, related_name='ratings_received', on_delete=models.CASCADE)
    rater = models.ForeignKey(User, related_name='ratings_given', on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 11)])  # 1-10 баллов
    comment = models.TextField(blank=True, max_length=200)
    created = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('rated_user', 'rater')  # Один друг = одна оценка
    
    def __str__(self):
        return f"{self.rater} -> {self.rated_user}: {self.rating}⭐"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)

    def __str__(self):
        return f'Profile of {self.user.username}'
    
    def get_average_rating(self):
        ratings = UserRating.objects.filter(rated_user=self.user)
        if ratings.exists():
            return round(ratings.aggregate(Avg('rating'))['rating__avg'], 1)
        return 0

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
