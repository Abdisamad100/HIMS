from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Profile, Policy, Member, Claim


# --- Inline Profile on User ---
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'


# --- Custom User Admin ---
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_role')
    list_select_related = ('profile',)
    search_fields = ('username', 'email', 'first_name', 'last_name')

    def get_role(self, instance):
        return instance.profile.role
    get_role.short_description = 'Role'

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)


# Unregister the default User admin, register our custom one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# --- Profile Admin ---
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email')


# --- Policy Admin ---
@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ('policy_number', 'name', 'premium', 'status', 'start_date', 'end_date')
    list_filter = ('status', 'start_date', 'end_date')
    search_fields = ('policy_number', 'name')
    ordering = ('-created_at',)


# --- Member Admin ---
@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'policy', 'phone', 'address', 'created_at')
    list_filter = ('policy',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'phone')
    ordering = ('-created_at',)


# --- Claim Admin ---
@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ('id', 'member', 'hospital', 'amount', 'status', 'date_of_service', 'created_at')
    list_filter = ('status', 'hospital')
    search_fields = ('member__user__username', 'hospital')
    ordering = ('-created_at',)
