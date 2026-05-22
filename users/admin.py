from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'profile'
    fk_name = 'user'


class UserProfileAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'get_full_name', 'is_staff', 'get_city', 'get_dark_mode')
    list_select_related = ('profile',)

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username
    get_full_name.short_description = 'Full name'

    def get_city(self, obj):
        return obj.profile.city if hasattr(obj, 'profile') else ''
    get_city.short_description = 'City'

    def get_dark_mode(self, obj):
        return obj.profile.dark_mode if hasattr(obj, 'profile') else False
    get_dark_mode.boolean = True
    get_dark_mode.short_description = 'Dark mode'

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)


admin.site.unregister(User)
admin.site.register(User, UserProfileAdmin)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'city', 'dark_mode', 'created_at')
    search_fields = ('user__username', 'city')
