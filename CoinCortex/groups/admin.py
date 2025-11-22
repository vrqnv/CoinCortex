from django.contrib import admin
from .models import Group, GroupPost, GroupMember, GroupRating, GroupSubscription


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator', 'created', 'get_subscribers_count', 'get_rating_count')
    list_filter = ('created',)
    search_fields = ('name', 'description', 'creator__username')
    readonly_fields = ('created',)
    
    def get_subscribers_count(self, obj):
        return obj.get_subscribers_count()
    get_subscribers_count.short_description = 'Подписчиков'
    
    def get_rating_count(self, obj):
        return obj.get_rating_count()
    get_rating_count.short_description = 'Оценок'


@admin.register(GroupPost)
class GroupPostAdmin(admin.ModelAdmin):
    list_display = ('group', 'author', 'created')
    list_filter = ('created', 'group')
    search_fields = ('content', 'author__username', 'group__name')
    readonly_fields = ('created',)


@admin.register(GroupMember)
class GroupMemberAdmin(admin.ModelAdmin):
    list_display = ('group', 'user', 'role', 'joined')
    list_filter = ('role', 'joined')
    search_fields = ('group__name', 'user__username')


@admin.register(GroupRating)
class GroupRatingAdmin(admin.ModelAdmin):
    list_display = ('group', 'user', 'rating', 'created')
    list_filter = ('rating', 'created')
    search_fields = ('group__name', 'user__username')


@admin.register(GroupSubscription)
class GroupSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('group', 'user', 'is_subscribed', 'subscribed_at')
    list_filter = ('is_subscribed', 'subscribed_at')
    search_fields = ('group__name', 'user__username')
