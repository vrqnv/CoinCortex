from django.contrib import admin
from .models import Post

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['author', 'content', 'created', 'likes_count']
    list_filter = ['created']
    search_fields = ['content', 'author__username']