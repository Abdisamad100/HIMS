from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Profile, Policy, Member, MemberPolicy, Claim, MemberPayment


# ==========================
#   INLINE PROFILE ON USER
# ==========================
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'


# ==========================
#       CUSTOM USER ADMIN
# ==========================
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


# Unregister default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# ==========================
#        PROFILE ADMIN
# ==========================
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email')


# ==========================
#        POLICY ADMIN
# ==========================
@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ('policy_number', 'name', 'premium', 'status', 'start_date', 'end_date')
    list_filter = ('status', 'start_date', 'end_date')
    search_fields = ('policy_number', 'name')
    ordering = ('name',)


# ==========================
#   INLINE MEMBER POLICIES
# ==========================
class MemberPolicyInline(admin.TabularInline):
    model = MemberPolicy
    extra = 1
    autocomplete_fields = ['policy']
    readonly_fields = ('member_policy_number', 'start_date',)
    verbose_name = "Policy Assignment"
    verbose_name_plural = "Policies Assigned"


# ==========================
#         MEMBER ADMIN
# ==========================
@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'address', 'registered_by')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'phone')
    inlines = [MemberPolicyInline]


# ==========================
#     MEMBER POLICY ADMIN
# ==========================
@admin.register(MemberPolicy)
class MemberPolicyAdmin(admin.ModelAdmin):
    list_display = ('member', 'policy', 'member_policy_number', 'is_active', 'start_date')
    list_filter = ('is_active', 'policy__status')
    search_fields = (
        'member__user__username',
        'member_policy_number',
        'policy__policy_number',
        'policy__name',
    )
    readonly_fields = ('member_policy_number', 'start_date')


# ==========================
#      MEMBER PAYMENT ADMIN
# ==========================
@admin.register(MemberPayment)
class MemberPaymentAdmin(admin.ModelAdmin):
    list_display = ('member_policy', 'amount', 'payment_date', 'transaction_id', 'recorded_by')
    search_fields = ('transaction_id', 'member_policy__member__user__username')
    list_filter = ('payment_date',)
    readonly_fields = ('transaction_id', 'payment_date')


# ==========================
#          CLAIM ADMIN
# ==========================
@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'get_member_name',
        'get_policy_number',
        'get_hospital',
        'amount',
        'status',
        'date_of_service',
        'created_at',
    )
    list_filter = ('status', 'hospital')
    search_fields = (
        'member_policy__member__user__username',
        'member_policy__policy__policy_number',
        'hospital__username',
    )
    ordering = ('-created_at',)

    def get_member_name(self, obj):
        if obj.member_policy and obj.member_policy.member and obj.member_policy.member.user:
            return obj.member_policy.member.user.get_full_name() or obj.member_policy.member.user.username
        return '-'
    get_member_name.short_description = 'Member'

    def get_policy_number(self, obj):
        if obj.member_policy and obj.member_policy.policy:
            return obj.member_policy.policy.policy_number
        return '-'
    get_policy_number.short_description = 'Policy No.'

    def get_hospital(self, obj):
        return obj.hospital.username if obj.hospital else '-'
    get_hospital.short_description = 'Hospital'
