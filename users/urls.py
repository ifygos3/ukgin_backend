from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'create_user', views.UserViewSet, basename='user')
router.register(r'wallets', views.WalletViewSet, basename='wallet')
router.register(r'wallet-transactions', views.WalletTransactionViewSet, basename='wallet-transaction')
router.register(r'kyc', views.KYCDocumentViewSet, basename='kyc')
router.register(r'donations', views.DonationViewSet, basename='donation')
router.register(r'deposits', views.DepositViewSet, basename='deposit')
router.register(r'withdrawals', views.WithdrawalViewSet, basename='withdrawal')
router.register(r'notifications', views.NotificationViewSet, basename='notification')
router.register(r'support-tickets', views.SupportTicketViewSet, basename='support-ticket')
router.register(r'ticket-replies', views.TicketReplyViewSet, basename='ticket-reply')
router.register(r'referrals', views.ReferralViewSet, basename='referral')
router.register(r'audit-logs', views.AuditLogViewSet, basename='audit-log')
router.register(r'system-settings', views.SystemSettingsViewSet, basename='system-settings')
router.register(r'login-history', views.LoginHistoryViewSet, basename='login-history')
router.register(r'events', views.AdminEventViewSet, basename='admin-event')
router.register(r'announcements', views.AdminAnnouncementViewSet, basename='announcement')
router.register(r'document-categories', views.AdminDocumentCategoryViewSet, basename='admin-document-category')
router.register(r'documents', views.AdminDocumentViewSet, basename='admin-document')
router.register(r'constitutions', views.AdminConstitutionViewSet, basename='admin-constitution')

urlpatterns = [
    path('', include(router.urls)),
    path('login/', views.CustomTokenObtainPairView.as_view(), name='login'),
    path('users/', views.UserListView.as_view(), name='user-list'),
    path('users/<int:user_id>/', views.UserDetailView.as_view(), name='user-detail'),
    path('users/profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('password-reset/', views.PasswordResetRequestView.as_view(), name='password-reset'),
    path('password-reset/confirm/', views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('public/events/', views.PublicEventsView.as_view(), name='public-events'),
    path('public/constitution/', views.PublicConstitutionView.as_view(), name='public-constitution'),
    path('public/documents/', views.PublicDocumentsView.as_view(), name='public-documents'),
    path('public/document-categories/', views.PublicDocumentCategoriesView.as_view(), name='public-document-categories'),
    path('public/state-chapters/', views.PublicStateChaptersView.as_view(), name='public-state-chapters'),
    path('public/state-chapters/<str:state>/members/', views.StateChapterMembersView.as_view(), name='state-chapter-members'),
    path('join-chapter/', views.JoinChapterView.as_view(), name='join-chapter'),
    path('public/event-responses/', views.PublicEventResponseListView.as_view(), name='public-event-responses'),
    path('event-responses/', views.UserEventResponseCreateView.as_view(), name='user-event-response-create'),
    path('event-responses/mine/', views.MyEventResponsesView.as_view(), name='my-event-responses'),
    path('admin/event-responses/', views.AdminEventResponseViewSet.as_view({'get': 'list', 'post': 'create'}), name='admin-event-responses'),
    path('dashboard/stats/', views.DashboardStatsView.as_view(), name='dashboard-stats'),
    path('dashboard/daily-registrations/', views.DailyRegistrationsView.as_view(), name='daily-registrations'),
    path('dashboard/monthly-registrations/', views.MonthlyRegistrationsView.as_view(), name='monthly-registrations'),
    path('dashboard/donation-analytics/', views.DonationAnalyticsView.as_view(), name='donation-analytics'),
    path('dashboard/profit-analytics/', views.ProfitAnalyticsView.as_view(), name='profit-analytics'),
    path('dashboard/user-activity/', views.UserActivityView.as_view(), name='user-activity'),
    path('export/', views.ExportReportView.as_view(), name='export-report'),
    path('public/announcements/', views.PublicAnnouncementListView.as_view(), name='public-announcements'),
]