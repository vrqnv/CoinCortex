from django.contrib import admin
from .models import (
    Post, PostLike, PostComment, Profile, Friendship,
    Chat, Message, Notification, Community
)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('author', 'wall_owner', 'created', 'community')
    list_filter = ('created', 'community')
    search_fields = ('content', 'author__username')


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    list_display = ('post', 'user', 'created')
    list_filter = ('created',)


@admin.register(PostComment)
class PostCommentAdmin(admin.ModelAdmin):
    list_display = ('post', 'author', 'created')
    list_filter = ('created',)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name')
    search_fields = ('user__username', 'first_name', 'last_name')


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ('from_user', 'to_user', 'accepted', 'created')
    list_filter = ('accepted', 'created')


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'updated')
    filter_horizontal = ('participants',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('chat', 'sender', 'created', 'read')
    list_filter = ('read', 'created')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'from_user', 'created', 'read')
    list_filter = ('notification_type', 'read', 'created')
    search_fields = ('user__username', 'from_user__username')


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator', 'created')
    list_filter = ('created',)
    search_fields = ('name', 'description')
    filter_horizontal = ('members',)

