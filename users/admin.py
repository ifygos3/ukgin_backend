from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import (
    Donation,
    Deposit,
    KYCDocument,
    Notification,
    User,
    Wallet,
    Withdrawal,
    Event,
    EventResponse,
    Announcement,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username',
        'email',
        'full_name',
        'role',
        'kyc_status',
        'is_active',
        'is_suspended',
        'is_banned',
        'created_at',
    )
    list_filter = (
        'role',
        'kyc_status',
        'is_active',
        'is_suspended',
        'is_banned',
        'is_staff',
        'is_superuser',
    )
    search_fields = (
        'username',
        'email',
        'full_name',
        'phone_number',
        'referral_code',
    )
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {
            'fields': (
                'full_name',
                'email',
                'phone_number',
                'address',
                'country',
                'state_of_origin',
                'lga',
                'community',
                'place_of_birth',
                'sex',
                'highest_qualification',
                'institution_attended',
                'year_of_graduation',
                'profession',
                'current_job',
                'job_title',
                'job_experience',
                'current_employee',
                'about_user',
            )
        }),
        (_('Account status'), {
            'fields': (
                'role',
                'is_active',
                'is_staff',
                'is_superuser',
                'is_suspended',
                'is_banned',
                'kyc_status',
                'referred_by',
                'referral_code',
                'ip_address',
                'device_info',
                'last_login_ip',
                'signature',
                'signature_data',
            )
        }),
        (_('Financial info'), {
            'fields': ('total_donations', 'total_deposits', 'total_withdrawals')
        }),
        (_('Important dates'), {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'full_name', 'password1', 'password2'),
        }),
    )
    actions = ['mark_as_suspended', 'mark_as_active', 'mark_as_banned', 'mark_as_unbanned', 'mark_as_unsuspended']

    @admin.action(description='Mark selected users as suspended')
    def mark_as_suspended(self, request, queryset):
        updated = queryset.update(is_suspended=True, is_banned=False)
        self.message_user(request, f'{updated} user(s) marked as suspended.', messages.WARNING)

    @admin.action(description='Mark selected users as active')
    def mark_as_active(self, request, queryset):
        updated = queryset.update(is_suspended=False, is_banned=False, is_active=True)
        self.message_user(request, f'{updated} user(s) marked as active.', messages.SUCCESS)

    @admin.action(description='Mark selected users as banned')
    def mark_as_banned(self, request, queryset):
        updated = queryset.update(is_banned=True, is_suspended=True, is_active=False)
        self.message_user(request, f'{updated} user(s) marked as banned.', messages.ERROR)

    @admin.action(description='Mark selected users as unbanned')
    def mark_as_unbanned(self, request, queryset):
        updated = queryset.update(is_banned=False, is_suspended=False, is_active=True)
        self.message_user(request, f'{updated} user(s) marked as unbanned.', messages.SUCCESS)


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'is_frozen', 'created_at')
    list_filter = ('is_frozen',)
    search_fields = ('user__username', 'user__email', 'user__full_name')


@admin.register(KYCDocument)
class KYCDocumentAdmin(admin.ModelAdmin):
    list_display = ('user', 'document_type', 'is_verified', 'created_at')
    list_filter = ('document_type', 'is_verified')
    search_fields = ('user__username', 'user__email', 'user__full_name')


@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'created_at')
    list_filter = ('status', 'payment_method')
    search_fields = ('user__username', 'user__email', 'user__full_name', 'transaction_reference')


@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'created_at')
    list_filter = ('status', 'payment_method')
    search_fields = ('user__username', 'user__email', 'user__full_name', 'transaction_reference')


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'payment_method', 'is_approved', 'created_at')
    list_filter = ('payment_method', 'is_approved')
    search_fields = ('user__username', 'user__email', 'user__full_name', 'transaction_reference')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'notification_type', 'sent_to_all', 'is_read', 'created_at')
    list_filter = ('notification_type', 'sent_to_all', 'is_read')
    search_fields = ('title', 'message')


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'event_type', 'event_date', 'location', 'is_featured', 'is_past', 'created_at')
    list_filter = ('event_type', 'is_featured', 'is_past')
    search_fields = ('name', 'location', 'description')
    ordering = ('-event_date',)


@admin.register(EventResponse)
class EventResponseAdmin(admin.ModelAdmin):
    list_display = ('event', 'user', 'response_type', 'created_at')
    list_filter = ('response_type',)
    search_fields = ('event__name', 'user__full_name', 'user__email', 'message')
    ordering = ('-created_at',)


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'author', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'message')
    ordering = ('-created_at',)
