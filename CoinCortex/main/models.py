from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    wall_owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wall_posts')
    content = models.TextField()
    created = models.DateTimeField(default=timezone.now)
    likes_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f'Post by {self.author.username}'