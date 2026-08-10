from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.urls import path, reverse
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    Donation,
    Deposit,
    KYCDocument,
    Notification,
    User,
    Wallet,
    WalletTransaction,
    Withdrawal,
    Event,
    EventResponse,
    Announcement,
    VolunteerApplication,
    NewsletterSubscription,
    Newsletter,
    ContactMessage,
    PageContent,
    Category,
    Post,
    Project,
    SocialMediaLink,
    ExecutiveLeader,
    GalleryImage,
    StateChapter,
    SupportTicket,
    TicketReply,
    Referral,
    AuditLog,
    SystemSettings,
    LoginHistory,
    DocumentCategory,
    Document,
    Constitution,
    Investment,
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
    readonly_fields = ('created_at', 'updated_at', 'unban_user_link')
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
                'email_verified',
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

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('unban/<int:user_id>/', self.admin_site.admin_view(self.unban_view), name='users_user_unban'),
        ]
        return custom_urls + urls

    def unban_view(self, request, user_id):
        if not self.has_change_permission(request):
            raise PermissionDenied
        from django.shortcuts import get_object_or_404
        user = get_object_or_404(self.model, pk=user_id)
        user.is_banned = False
        user.is_suspended = False
        user.is_active = True
        user.save()
        self.message_user(request, f'User {user.username} has been unbanned.', messages.SUCCESS)
        return redirect(reverse('admin:users_user_change', args=[user_id]))

    def unban_user_link(self, obj):
        if not obj:
            return ""
        if obj.is_banned:
            url = reverse('admin:users_user_unban', args=[obj.pk])
            return format_html('<a class="button" href="{}">Unban user</a>', url)
        return format_html('<span style="color:green;">Not banned</span>')
    unban_user_link.short_description = 'Unban'

    def save_model(self, request, obj, form, change):
        is_new = not obj.pk
        super().save_model(request, obj, form, change)
        if is_new and obj.email and not obj.email_verified:
            try:
                token = RefreshToken.for_user(obj)
                verification_url = f"{settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:5173'}/verify-email?token={str(token.access_token)}&email={obj.email}"
                send_mail(
                    'UKGIN - Verify Your Email',
                    f'Click the link to verify your email: {verification_url}',
                    settings.DEFAULT_FROM_EMAIL,
                    [obj.email],
                    fail_silently=True,
                )
            except Exception:
                pass


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


@admin.register(VolunteerApplication)
class VolunteerApplicationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'status', 'is_reviewed', 'created_at')
    list_filter = ('status', 'is_reviewed', 'availability', 'created_at')
    search_fields = ('full_name', 'email', 'skills')
    ordering = ('-created_at',)
    actions = ['mark_reviewed', 'accept_application', 'reject_application']

    @admin.action(description='Mark as reviewed')
    def mark_reviewed(self, request, queryset):
        queryset.update(is_reviewed=True)
        self.message_user(request, f'{queryset.count()} application(s) marked as reviewed.')

    @admin.action(description='Accept applications')
    def accept_application(self, request, queryset):
        queryset.update(is_reviewed=True, status='accepted')
        self.message_user(request, f'{queryset.count()} application(s) accepted.')

    @admin.action(description='Reject applications')
    def reject_application(self, request, queryset):
        queryset.update(is_reviewed=True, status='rejected')
        self.message_user(request, f'{queryset.count()} application(s) rejected.', messages.ERROR)


@admin.register(NewsletterSubscription)
class NewsletterSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_subscribed', 'created_at')
    list_filter = ('is_subscribed', 'created_at')
    search_fields = ('email',)
    ordering = ('-created_at',)


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ('subject', 'sent_to_all', 'created_at')
    list_filter = ('sent_to_all', 'created_at')
    search_fields = ('subject', 'message')
    ordering = ('-created_at',)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'is_read', 'responded', 'created_at')
    list_filter = ('is_read', 'responded', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    ordering = ('-created_at',)


@admin.register(PageContent)
class PageContentAdmin(admin.ModelAdmin):
    list_display = ('title', 'page_type', 'is_published', 'created_at')
    list_filter = ('page_type', 'is_published', 'created_at')
    search_fields = ('title', 'content', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    ordering = ('-created_at',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'post_type', 'category', 'is_published', 'is_featured', 'published_date', 'view_count')
    list_filter = ('post_type', 'is_published', 'is_featured', 'category', 'created_at')
    search_fields = ('title', 'excerpt', 'content')
    prepopulated_fields = {'slug': ('title',)}
    ordering = ('-published_date', '-created_at')
    actions = ['publish', 'unpublish', 'feature', 'unfeature']

    @admin.action(description='Publish selected posts')
    def publish(self, request, queryset):
        queryset.update(is_published=True)
        self.message_user(request, f'{queryset.count()} post(s) published.')

    @admin.action(description='Unpublish selected posts')
    def unpublish(self, request, queryset):
        queryset.update(is_published=False)
        self.message_user(request, f'{queryset.count()} post(s) unpublished.')

    @admin.action(description='Feature selected posts')
    def feature(self, request, queryset):
        queryset.update(is_featured=True)
        self.message_user(request, f'{queryset.count()} post(s) featured.')

    @admin.action(description='Unfeature selected posts')
    def unfeature(self, request, queryset):
        queryset.update(is_featured=False)
        self.message_user(request, f'{queryset.count()} post(s) unfeatured.')


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_active', 'is_featured', 'start_date', 'end_date')
    list_filter = ('is_active', 'is_featured', 'category', 'created_at')
    search_fields = ('title', 'description', 'content')
    prepopulated_fields = {'slug': ('title',)}
    ordering = ('-created_at',)


@admin.register(SocialMediaLink)
class SocialMediaLinkAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'is_active', 'order')
    list_filter = ('is_active', 'name')
    search_fields = ('name', 'url')
    ordering = ('order', 'name')


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'order', 'media_type', 'created_at')
    list_filter = ('is_active', 'order', 'created_at')
    search_fields = ('title', 'description')
    ordering = ('order', '-created_at')
    readonly_fields = ('media_preview',)
    fields = ('title', 'description', 'image', 'is_active', 'order', 'media_preview', 'created_at', 'updated_at')

    def media_preview(self, obj):
        if not obj or not obj.image:
            return ""
        try:
            url = obj.image.url
        except Exception:
            return ""
        if obj.is_video():
            return format_html(
                '<video width="320" controls><source src="{}" type="video/mp4">Your browser does not support the video tag.</video>',
                url,
            )
        return format_html('<img src="{}" style="max-width: 400px; max-height: 300px;" />', url)
    media_preview.short_description = 'Preview'


@admin.register(ExecutiveLeader)
class ExecutiveLeaderAdmin(admin.ModelAdmin):
    list_display = ('name', 'position', 'is_active', 'order')
    list_filter = ('is_active', 'position')
    search_fields = ('name', 'position', 'bio')
    ordering = ('order', 'name')


@admin.register(StateChapter)
class StateChapterAdmin(admin.ModelAdmin):
    list_display = ('state', 'coordinator', 'email', 'phone', 'is_active', 'order')
    list_filter = ('is_active', 'state')
    search_fields = ('state', 'coordinator', 'email', 'phone')
    ordering = ('order', 'state')
    fields = ('state', 'coordinator', 'email', 'phone', 'address', 'description', 'is_active', 'order')


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'transaction_type', 'amount', 'reference', 'created_at')
    list_filter = ('transaction_type',)
    search_fields = ('wallet__user__username', 'wallet__user__email', 'reference')
    ordering = ('-created_at',)


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('subject', 'user', 'status', 'priority', 'created_at')
    list_filter = ('status', 'priority')
    search_fields = ('subject', 'user__username', 'user__email')
    ordering = ('-created_at',)


@admin.register(TicketReply)
class TicketReplyAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'author', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('ticket__subject', 'author__username', 'message')
    ordering = ('-created_at',)


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('referrer', 'referred_user', 'reward_amount', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('referrer__username', 'referred_user__username')
    ordering = ('-created_at',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'admin_user', 'ip_address', 'created_at')
    list_filter = ('action',)
    search_fields = ('admin_user__username', 'ip_address', 'details')
    ordering = ('-created_at',)
    readonly_fields = ('action', 'admin_user', 'ip_address', 'details', 'created_at')


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'updated_at')
    search_fields = ('site_name',)
    ordering = ('site_name',)


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'ip_address', 'device_info', 'is_successful', 'created_at')
    list_filter = ('is_successful',)
    search_fields = ('user__username', 'ip_address')
    ordering = ('-created_at',)


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'description')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_public', 'is_receipt', 'created_at')
    list_filter = ('category', 'is_public', 'is_receipt')
    search_fields = ('title', 'description')
    ordering = ('-created_at',)


@admin.register(Constitution)
class ConstitutionAdmin(admin.ModelAdmin):
    list_display = ('title', 'version', 'is_current', 'effective_date', 'created_at')
    list_filter = ('is_current',)
    search_fields = ('title', 'content')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan_name', 'amount_invested', 'status', 'created_at')
    list_filter = ('plan_name', 'status')
    search_fields = ('user__username', 'user__email', 'reference')
    ordering = ('-created_at',)
