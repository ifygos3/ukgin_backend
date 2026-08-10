from rest_framework import viewsets, permissions, status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action, api_view, permission_classes
from django.db.models import Sum, Count, Q, Avg
from django.db import OperationalError
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from .models import User, Wallet, WalletTransaction, KYCDocument, Donation, Deposit, Withdrawal, Notification, SupportTicket, TicketReply, Referral, AuditLog, SystemSettings, LoginHistory, Event, EventResponse, DocumentCategory, Document, Constitution, Announcement, VolunteerApplication, NewsletterSubscription, Newsletter, ContactMessage, PageContent, Category, Post, Project, SocialMediaLink, ExecutiveLeader, GalleryImage, StateChapter, Partner, Sponsor
from .serializers import (
    UserSerializer, RegisterSerializer, WalletSerializer, WalletTransactionSerializer,
    KYCDocumentSerializer, DonationSerializer, DepositSerializer, WithdrawalSerializer,
    NotificationSerializer, SupportTicketSerializer,
    TicketReplySerializer, ReferralSerializer, AuditLogSerializer, SystemSettingsSerializer,
    LoginHistorySerializer, DashboardStatsSerializer,
    EventSerializer, EventResponseSerializer, PublicEventResponseSerializer, PublicUserSerializer, DocumentCategorySerializer, DocumentSerializer, ConstitutionSerializer,
    AnnouncementSerializer, PublicAnnouncementSerializer,
    VolunteerApplicationSerializer, VolunteerApplicationAdminSerializer, NewsletterSubscriptionSerializer, NewsletterSerializer, ContactMessageSerializer, ContactMessageAdminSerializer, PageContentSerializer, CategorySerializer, PostSerializer, ProjectSerializer, SocialMediaLinkSerializer, ExecutiveLeaderSerializer, GalleryImageSerializer, StateChapterSerializer, PartnerSerializer, SponsorSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail, EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
import json
import time
import uuid


User = get_user_model()


class StandardPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.role in ('admin', 'super_admin') or request.user.is_staff
        )


class IsAdminOrFinance(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.role in ('admin', 'super_admin', 'finance_manager') or request.user.is_staff
        )


class IsAdminOrSupport(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.role in ('admin', 'super_admin', 'support_staff') or request.user.is_staff
        )


ROLE_CHOICES = [
    ('member', 'Member'),
    ('support_staff', 'Support Staff'),
    ('finance_manager', 'Finance Manager'),
    ('admin', 'Admin'),
    ('super_admin', 'Super Admin'),
]

class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        start_time = time.perf_counter()
        data = request.data
        identifier = data.get('username') or data.get('email') or data.get('phone_number')
        password = data.get('password')
        remember_me = data.get('remember_me', False)

        if not identifier:
            print('LOGIN DEBUG - no identifier')
            return Response({'detail': 'Username, email, or phone number is required'}, status=400)
        if not password:
            print('LOGIN DEBUG - no password')
            return Response({'detail': 'Password is required'}, status=400)

        user = None
        try:
            if identifier:
                user = User.objects.filter(username=identifier).first()
                print('LOGIN DEBUG - username lookup:', user.username if user else None)
                if not user:
                    user = User.objects.filter(email=identifier).first()
                    print('LOGIN DEBUG - email lookup:', user.username if user else None)
                if not user:
                    user = User.objects.filter(phone_number=identifier).first()
                    print('LOGIN DEBUG - phone lookup:', user.username if user else None)
        except OperationalError:
            print('LOGIN DEBUG - database connection error')
            return Response({'detail': 'Database connection error. Please try again later.'}, status=500)

        if not user:
            print('LOGIN DEBUG - user not found for identifier:', repr(identifier))
            try:
                AuditLog.objects.create(
                    admin_user=None,
                    action='login_failed',
                    details=f'Failed login attempt for identifier: {identifier}',
                    ip_address=request.META.get('REMOTE_ADDR', ''),
                )
            except OperationalError:
                pass
            return Response({'detail': 'Invalid credentials'}, status=400)

        print('LOGIN DEBUG - password check result:', user.check_password(password))
        if not user.check_password(password):
            try:
                AuditLog.objects.create(
                    admin_user=user,
                    action='login_failed',
                    details=f'Failed password attempt for user: {user.username}',
                    ip_address=request.META.get('REMOTE_ADDR', ''),
                )
                LoginHistory.objects.create(
                    user=user,
                    ip_address=request.META.get('REMOTE_ADDR', ''),
                    device_info=request.META.get('HTTP_USER_AGENT', ''),
                    is_successful=False,
                )
            except OperationalError:
                pass
            return Response({'detail': 'Invalid credentials'}, status=400)

        if user.is_suspended:
            return Response({'detail': 'Your account has been suspended. Please contact support.'}, status=403)
        if user.is_banned:
            return Response({'detail': 'Your account has been banned. Please contact support.'}, status=403)
        if not user.is_active:
            return Response({'detail': 'Your account has been deactivated. Please contact support.'}, status=403)
        if not user.email_verified and not (user.role in ('admin', 'super_admin') or user.is_staff):
            return Response({'detail': 'Please verify your email before logging in. Check your inbox for the verification link.'}, status=403)

        if remember_me:
            access_token_lifetime = timedelta(days=30)
            refresh_token_lifetime = timedelta(days=30)
        else:
            access_token_lifetime = getattr(settings, 'SIMPLE_JWT', {}).get('ACCESS_TOKEN_LIFETIME', timedelta(minutes=60))
            refresh_token_lifetime = getattr(settings, 'SIMPLE_JWT', {}).get('REFRESH_TOKEN_LIFETIME', timedelta(days=1))

        refresh = RefreshToken.for_user(user)
        refresh.access_token.lifetime = access_token_lifetime
        refresh.lifetime = refresh_token_lifetime

        LoginHistory.objects.create(
            user=user,
            ip_address=request.META.get('REMOTE_ADDR', ''),
            device_info=request.META.get('HTTP_USER_AGENT', ''),
            is_successful=True,
        )

        AuditLog.objects.create(
            admin_user=user,
            action='login',
            details=f'User {user.username} logged in successfully',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        elapsed = time.perf_counter() - start_time

        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    pagination_class = StandardPagination

    def get_serializer_class(self):
        if self.action == 'create':
            return RegisterSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        elif self.action == 'create':
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [p() for p in permission_classes]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        Wallet.objects.get_or_create(user=user)
        Referral.objects.filter(referred_user=user).update(status='completed')
        try:
            token = RefreshToken.for_user(user)
            verification_url = f"{request.data.get('frontend_url', 'http://localhost:5173')}/verify-email?token={str(token.access_token)}&email={user.email}"
            send_mail(
                'UKGIN - Verify Your Email',
                f'Click the link to verify your email: {verification_url}',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            )
        except Exception:
            pass
        AuditLog.objects.create(
            admin_user=request.user if request.user.is_authenticated else None,
            action='user_create',
            target_user=user,
            details=f'User {user.username} created',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )
        headers = self.get_success_headers(serializer.data)
        return Response({'user': UserSerializer(user).data}, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        old_data = UserSerializer(instance).data
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        AuditLog.objects.create(
            admin_user=request.user,
            action='user_update',
            target_user=user,
            details=f'User {user.username} updated',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )
        return Response({'status': 'success', 'message': 'User updated successfully', 'data': UserSerializer(user).data})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        username = instance.username
        instance.delete()
        AuditLog.objects.create(
            admin_user=request.user,
            action='user_delete',
            details=f'User {username} deleted',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )
        return Response({'status': 'success', 'message': f'User {username} deleted successfully'}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.is_suspended = False
        user.save()
        AuditLog.objects.create(
            admin_user=request.user,
            action='user_activate',
            target_user=user,
            details=f'User {user.username} activated',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )
        return Response({'status': 'success', 'message': f'User {user.username} activated'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def suspend(self, request, pk=None):
        user = self.get_object()
        user.is_suspended = True
        user.is_active = False
        user.save()
        AuditLog.objects.create(
            admin_user=request.user,
            action='user_suspend',
            target_user=user,
            details=f'User {user.username} suspended',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )
        return Response({'status': 'success', 'message': f'User {user.username} suspended'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def ban(self, request, pk=None):
        user = self.get_object()
        user.is_banned = True
        user.is_active = False
        user.is_suspended = True
        user.save()
        AuditLog.objects.create(
            admin_user=request.user,
            action='user_ban',
            target_user=user,
            details=f'User {user.username} banned',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )
        return Response({'status': 'success', 'message': f'User {user.username} banned'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def unban(self, request, pk=None):
        user = self.get_object()
        user.is_banned = False
        user.is_suspended = False
        user.is_active = True
        user.save()
        AuditLog.objects.create(
            admin_user=request.user,
            action='user_unban',
            target_user=user,
            details=f'User {user.username} unbanned',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )
        return Response({'status': 'success', 'message': f'User {user.username} unbanned'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def unsuspend(self, request, pk=None):
        user = self.get_object()
        user.is_suspended = False
        user.is_active = True
        user.save()
        AuditLog.objects.create(
            admin_user=request.user,
            action='user_unsuspend',
            target_user=user,
            details=f'User {user.username} unsuspended',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )
        return Response({'status': 'success', 'message': f'User {user.username} unsuspended'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def reset_password(self, request, pk=None):
        user = self.get_object()
        new_password = request.data.get('new_password', 'DefaultPass123!')
        user.set_password(new_password)
        user.save()
        AuditLog.objects.create(
            admin_user=request.user,
            action='user_reset_password',
            target_user=user,
            details=f'Password reset for user {user.username}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )
        return Response({'status': 'success', 'message': f'Password reset for {user.username}'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def assign_role(self, request, pk=None):
        user = self.get_object()
        new_role = request.data.get('role')
        if new_role and new_role in dict(ROLE_CHOICES):
            user.role = new_role
            user.save()
            AuditLog.objects.create(
                admin_user=request.user,
                action='user_role_change',
                target_user=user,
                details=f'Role changed to {new_role} for user {user.username}',
                ip_address=request.META.get('REMOTE_ADDR', ''),
            )
            return Response({'status': 'success', 'message': f'Role updated to {new_role}'})
        return Response({'status': 'error', 'message': 'Invalid role'}, status=400)

    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def export(self, request):
        users = User.objects.all()
        export_format = request.query_params.get('format', 'json')
        if export_format == 'csv':
            import csv
            from django.http import HttpResponse
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="users.csv"'
            writer = csv.writer(response)
            writer.writerow(['ID', 'Username', 'Email', 'Full Name', 'Role', 'Status', 'Created'])
            for u in users:
                writer.writerow([u.id, u.username, u.email, u.full_name, u.role, 'Active' if u.is_active else 'Inactive', u.created_at])
            return response
        elif export_format == 'excel':
            import openpyxl
            from django.http import HttpResponse
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Users'
            ws.append(['ID', 'Username', 'Email', 'Full Name', 'Role', 'Status', 'Created'])
            for u in users:
                ws.append([u.id, u.username, u.email, u.full_name, u.role, 'Active' if u.is_active else 'Inactive', u.created_at])
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="users.xlsx"'
            wb.save(response)
            return response
        return Response({'users': UserSerializer(users, many=True).data})


class WalletViewSet(viewsets.ModelViewSet):
    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAdminUser]

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def credit(self, request, pk=None):
        wallet = self.get_object()
        amount = request.data.get('amount')
        description = request.data.get('description', '')
        reference = request.data.get('reference', str(uuid.uuid4()))
        if not amount or float(amount) <= 0:
            return Response({'status': 'error', 'message': 'Invalid amount'}, status=400)
        wallet.balance += float(amount)
        wallet.save()
        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type='credit',
            amount=amount,
            description=description,
            reference=reference,
        )
        AuditLog.objects.create(
            admin_user=request.user,
            action='wallet_credit',
            target_user=wallet.user,
            details=f'Credited {amount} to {wallet.user.username} wallet',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )
        return Response({'status': 'success', 'wallet': WalletSerializer(wallet).data})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def debit(self, request, pk=None):
        wallet = self.get_object()
        amount = request.data.get('amount')
        description = request.data.get('description', '')
        reference = request.data.get('reference', str(uuid.uuid4()))
        if not amount or float(amount) <= 0:
            return Response({'status': 'error', 'message': 'Invalid amount'}, status=400)
        if wallet.balance < float(amount):
            return Response({'status': 'error', 'message': 'Insufficient balance'}, status=400)
        wallet.balance -= float(amount)
        wallet.save()
        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type='debit',
            amount=amount,
            description=description,
            reference=reference,
        )
        AuditLog.objects.create(
            admin_user=request.user,
            action='wallet_debit',
            target_user=wallet.user,
            details=f'Debited {amount} from {wallet.user.username} wallet',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )
        return Response({'status': 'success', 'wallet': WalletSerializer(wallet).data})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def freeze(self, request, pk=None):
        wallet = self.get_object()
        wallet.is_frozen = True
        wallet.save()
        AuditLog.objects.create(
            admin_user=request.user,
            action='wallet_freeze',
            target_user=wallet.user,
            details=f'Wallet frozen for {wallet.user.username}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )
        return Response({'status': 'success', 'message': f'Wallet frozen for {wallet.user.username}'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def unfreeze(self, request, pk=None):
        wallet = self.get_object()
        wallet.is_frozen = False
        wallet.save()
        AuditLog.objects.create(
            admin_user=request.user,
            action='wallet_unfreeze',
            target_user=wallet.user,
            details=f'Wallet unfrozen for {wallet.user.username}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )
        return Response({'status': 'success', 'message': f'Wallet unfrozen for {wallet.user.username}'})


class WalletTransactionViewSet(viewsets.ModelViewSet):
    queryset = WalletTransaction.objects.all().order_by('-created_at')
    serializer_class = WalletTransactionSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        wallet_id = self.request.query_params.get('wallet_id')
        if wallet_id:
            return self.queryset.filter(wallet_id=wallet_id)
        return self.queryset


class KYCDocumentViewSet(viewsets.ModelViewSet):
    queryset = KYCDocument.objects.all().order_by('-created_at')
    serializer_class = KYCDocumentSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        status_filter = self.request.query_params.get('status')
        if status_filter:
            if status_filter == 'pending':
                return self.queryset.filter(is_verified=False)
            elif status_filter == 'approved':
                return self.queryset.filter(is_verified=True)
            elif status_filter == 'rejected':
                return self.queryset.filter(rejection_reason__isnull=False, is_verified=False)
        return self.queryset

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        kyc = self.get_object()
        kyc.is_verified = True
        kyc.verified_by = request.user
        kyc.user.kyc_status = 'approved'
        kyc.user.save()
        kyc.save()
        AuditLog.objects.create(
            admin_user=request.user,
            action='kyc_approve',
            target_user=kyc.user,
            details=f'KYC approved for {kyc.user.username}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )
        return Response({'status': 'success', 'message': f'KYC approved for {kyc.user.full_name}'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def reject(self, request, pk=None):
        kyc = self.get_object()
        reason = request.data.get('reason', '')
        kyc.rejection_reason = reason
        kyc.is_verified = False
        kyc.verified_by = request.user
        kyc.user.kyc_status = 'rejected'
        kyc.user.save()
        kyc.save()
        AuditLog.objects.create(
            admin_user=request.user,
            action='kyc_reject',
            target_user=kyc.user,
            details=f'KYC rejected for {kyc.user.username}: {reason}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )
        return Response({'status': 'success', 'message': f'KYC rejected for {kyc.user.full_name}'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def request_resubmission(self, request, pk=None):
        kyc = self.get_object()
        kyc.user.kyc_status = 'resubmission'
        kyc.user.save()
        AuditLog.objects.create(
            admin_user=request.user,
            action='kyc_reject',
            target_user=kyc.user,
            details=f'Resubmission requested for {kyc.user.username}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )
        return Response({'status': 'success', 'message': f'Resubmission requested for {kyc.user.full_name}'})


class DonationViewSet(viewsets.ModelViewSet):
    queryset = Donation.objects.all().order_by('-created_at')
    serializer_class = DonationSerializer
    pagination_class = StandardPagination
    def get_permissions(self):
        if self.action in ["create", "list", "retrieve"]:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [IsAdminOrFinance]
        return [p() for p in permission_classes]

    def get_queryset(self):
        status = self.request.query_params.get('status')
        if status == 'approved':
            return self.queryset.filter(is_approved=True)
        elif status == 'pending':
            return self.queryset.filter(is_approved=False)
        elif status == 'rejected':
            return self.queryset.filter(is_approved=False)
        return self.queryset

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrFinance])
    def approve(self, request, pk=None):
        donation = self.get_object()
        donation.is_approved = True
        donation.approved_by = request.user
        donation.user.total_donations += donation.amount
        donation.user.save()
        donation.save()
        AuditLog.objects.create(
            admin_user=request.user,
            action='donation_approve',
            target_user=donation.user,
            details=f'Donation of {donation.amount} approved for {donation.user.username}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )
        return Response({'status': 'success', 'message': 'Donation approved'})


class DepositViewSet(viewsets.ModelViewSet):
    queryset = Deposit.objects.all().order_by('-created_at')
    serializer_class = DepositSerializer
    pagination_class = StandardPagination
    def get_permissions(self):
        if self.action in ["create", "list", "retrieve"]:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [IsAdminOrFinance]
        return [p() for p in permission_classes]

    def get_queryset(self):
        status = self.request.query_params.get('status')
        method = self.request.query_params.get('payment_method')
        qs = self.queryset
        if status:
            qs = qs.filter(status=status)
        if method:
            qs = qs.filter(payment_method=method)
        return qs

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrFinance])
    def approve(self, request, pk=None):
        deposit = self.get_object()
        deposit.status = 'approved'
        deposit.approved_by = request.user
        deposit.user.total_deposits += deposit.amount
        deposit.user.save()
        deposit.save()
        wallet, _ = Wallet.objects.get_or_create(user=deposit.user)
        wallet.balance += deposit.amount
        wallet.save()
        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type='credit',
            amount=deposit.amount,
            description=f'Deposit approved - {deposit.amount}',
            reference=f'DEP-{deposit.id}',
        )
        AuditLog.objects.create(
            admin_user=request.user,
            action='deposit_approve',
            target_user=deposit.user,
            details=f'Deposit of {deposit.amount} approved for {deposit.user.username}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )
        return Response({'status': 'success', 'message': 'Deposit approved'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrFinance])
    def reject(self, request, pk=None):
        deposit = self.get_object()
        deposit.status = 'rejected'
        deposit.approved_by = request.user
        deposit.save()
        AuditLog.objects.create(
            admin_user=request.user,
            action='deposit_reject',
            target_user=deposit.user,
            details=f'Deposit of {deposit.amount} rejected for {deposit.user.username}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )
        return Response({'status': 'success', 'message': 'Deposit rejected'})


class WithdrawalViewSet(viewsets.ModelViewSet):
    queryset = Withdrawal.objects.all().order_by('-created_at')
    serializer_class = WithdrawalSerializer
    pagination_class = StandardPagination
    def get_permissions(self):
        if self.action in ["create", "list", "retrieve"]:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [IsAdminOrFinance]
        return [p() for p in permission_classes]

    def get_queryset(self):
        status = self.request.query_params.get('status')
        qs = self.queryset
        if status:
            qs = qs.filter(status=status)
        return qs

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrFinance])
    def approve(self, request, pk=None):
        withdrawal = self.get_object()
        withdrawal.status = 'approved'
        withdrawal.processed_by = request.user
        wallet, _ = Wallet.objects.get_or_create(user=withdrawal.user)
        if wallet.balance < withdrawal.amount:
            return Response({'status': 'error', 'message': 'Insufficient wallet balance'}, status=400)
        wallet.balance -= withdrawal.amount
        wallet.save()
        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type='debit',
            amount=withdrawal.amount,
            description=f'Withdrawal approved - {withdrawal.amount}',
            reference=f'WTH-{withdrawal.id}',
        )
        withdrawal.save()
        AuditLog.objects.create(
            admin_user=request.user,
            action='withdrawal_approve',
            target_user=withdrawal.user,
            details=f'Withdrawal of {withdrawal.amount} approved for {withdrawal.user.username}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )
        return Response({'status': 'success', 'message': 'Withdrawal approved'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrFinance])
    def reject(self, request, pk=None):
        withdrawal = self.get_object()
        withdrawal.status = 'rejected'
        withdrawal.processed_by = request.user
        withdrawal.save()
        AuditLog.objects.create(
            admin_user=request.user,
            action='withdrawal_reject',
            target_user=withdrawal.user,
            details=f'Withdrawal of {withdrawal.amount} rejected for {withdrawal.user.username}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )
        return Response({'status': 'success', 'message': 'Withdrawal rejected'})


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.select_related('user', 'announcement').all().order_by('-created_at')
    serializer_class = NotificationSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        notification = serializer.save(sent_by=self.request.user)
        if notification.sent_to_all:
            users = User.objects.all()
            notification.target_users.set(users)
        AuditLog.objects.create(
            admin_user=self.request.user,
            action='notification_send',
            details=f'Notification "{notification.title}" sent',
            ip_address=self.request.META.get('REMOTE_ADDR', ''),
        )


class SupportTicketViewSet(viewsets.ModelViewSet):
    queryset = SupportTicket.objects.select_related('user', 'assigned_to').all().order_by('-created_at')
    serializer_class = SupportTicketSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAdminOrSupport]

    def get_queryset(self):
        priority = self.request.query_params.get('priority')
        status_filter = self.request.query_params.get('status')
        qs = self.queryset
        if priority:
            qs = qs.filter(priority=priority)
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrSupport])
    def close(self, request, pk=None):
        ticket = self.get_object()
        ticket.status = 'closed'
        ticket.save()
        AuditLog.objects.create(
            admin_user=request.user,
            action='ticket_close',
            target_user=ticket.user,
            details=f'Ticket "{ticket.subject}" closed',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )
        return Response({'status': 'success', 'message': 'Ticket closed'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrSupport])
    def reopen(self, request, pk=None):
        ticket = self.get_object()
        ticket.status = 'reopened'
        ticket.save()
        AuditLog.objects.create(
            admin_user=request.user,
            action='ticket_reopen',
            target_user=ticket.user,
            details=f'Ticket "{ticket.subject}" reopened',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )
        return Response({'status': 'success', 'message': 'Ticket reopened'})


class TicketReplyViewSet(viewsets.ModelViewSet):
    queryset = TicketReply.objects.all().order_by('created_at')
    serializer_class = TicketReplySerializer
    pagination_class = StandardPagination
    permission_classes = [IsAdminOrSupport]

    def perform_create(self, serializer):
        ticket_id = self.kwargs.get('ticket_pk')
        ticket = get_object_or_404(SupportTicket, id=ticket_id)
        reply = serializer.save(author=self.request.user, ticket=ticket)
        ticket.status = 'in_progress'
        ticket.save()


class ReferralViewSet(viewsets.ModelViewSet):
    queryset = Referral.objects.all().order_by('-created_at')
    serializer_class = ReferralSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAdminUser]


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related('user').all().order_by('-created_at')
    serializer_class = AuditLogSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        action = self.request.query_params.get('action')
        user_id = self.request.query_params.get('user_id')
        qs = self.queryset
        if action:
            qs = qs.filter(action=action)
        if user_id:
            qs = qs.filter(target_user_id=user_id)
        return qs


class SystemSettingsViewSet(viewsets.ModelViewSet):
    queryset = SystemSettings.objects.all()
    serializer_class = SystemSettingsSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return self.queryset.all()[:1]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_queryset().first()
        if not instance:
            instance = SystemSettings.objects.create()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_queryset().first()
        if not instance:
            instance = SystemSettings.objects.create()
        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.get('partial', False))
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class LoginHistoryViewSet(viewsets.ModelViewSet):
    queryset = LoginHistory.objects.select_related('user').all().order_by('-created_at')
    serializer_class = LoginHistorySerializer
    pagination_class = StandardPagination
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        user_id = self.request.query_params.get('user_id')
        qs = self.queryset
        if user_id:
            qs = qs.filter(user_id=user_id)
        return qs


class DashboardStatsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True, is_suspended=False, is_banned=False).count()
        suspended_users = User.objects.filter(is_suspended=True).count()
        pending_kyc = User.objects.filter(kyc_status='pending').count()
        approved_kyc = User.objects.filter(kyc_status='approved').count()
        total_donations = Donation.objects.filter(is_approved=True).aggregate(total=Sum('amount'))['total'] or 0
        total_deposits = Deposit.objects.aggregate(total=Sum('amount'))['total'] or 0
        pending_deposits = Deposit.objects.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0
        approved_deposits = Deposit.objects.filter(status='approved').aggregate(total=Sum('amount'))['total'] or 0
        monthly_revenue = Donation.objects.filter(
            is_approved=True,
            created_at__gte=month_start
        ).aggregate(total=Sum('amount'))['total'] or 0
        total_platform_balance = Wallet.objects.aggregate(total=Sum('balance'))['total'] or 0

        stats = {
            'total_users': total_users,
            'active_users': active_users,
            'suspended_users': suspended_users,
            'pending_members': User.objects.filter(is_active=False).count(),
            'pending_kyc': pending_kyc,
            'approved_kyc': approved_kyc,
            'total_donations': float(total_donations),
            'total_deposits': float(total_deposits),
            'pending_deposits': float(pending_deposits),
            'approved_deposits': float(approved_deposits),
            'monthly_revenue': float(monthly_revenue),
            'total_platform_balance': float(total_platform_balance),
            'total_events': 0,
            'total_news': 0,
            'total_projects': 0,
            'total_gallery': 0,
            'total_downloads': 0,
            'total_volunteers': 0,
            'total_partners': 0,
            'total_sponsors': 0,
            'total_states': 0,
            'total_lgas': 0,
            'total_notifications': 0,
            'total_reports': 0,
            'recent_logins': LoginHistory.objects.filter(created_at__gte=timezone.now() - timedelta(days=1)).count(),
        }
        return Response(stats)


class DailyRegistrationsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        registrations = User.objects.filter(
            date_joined__gte=start_date,
            date_joined__lte=end_date
        ).values('date_joined__date').annotate(count=Count('id')).order_by('date_joined__date')
        data = [{'date': str(r['date_joined__date']), 'count': r['count']} for r in registrations]
        return Response(data)


class MonthlyRegistrationsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        months = int(request.query_params.get('months', 12))
        end_date = timezone.now()
        start_date = end_date - timedelta(days=months * 30)
        registrations = User.objects.filter(
            date_joined__gte=start_date,
            date_joined__lte=end_date
        ).values('date_joined__year', 'date_joined__month').annotate(count=Count('id')).order_by('date_joined__year', 'date_joined__month')
        data = [{'year': r['date_joined__year'], 'month': r['date_joined__month'], 'count': r['count']} for r in registrations]
        return Response(data)


class DonationAnalyticsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        donations = Donation.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date,
            is_approved=True
        ).values('created_at__date').annotate(total=Sum('amount'), count=Count('id')).order_by('created_at__date')
        data = [{'date': str(d['created_at__date']), 'total': float(d['total']), 'count': d['count']} for d in donations]
        return Response(data)


class ProfitAnalyticsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        deposits = Deposit.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date,
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0
        withdrawals = Withdrawal.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date,
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0
        donations = Donation.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date,
            is_approved=True
        ).aggregate(total=Sum('amount'))['total'] or 0
        profit = float(donations) - float(withdrawals)
        return Response({
            'total_deposits': float(deposits),
            'total_withdrawals': float(withdrawals),
            'total_donations': float(donations),
            'profit': profit,
        })


class UserActivityView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        logins = LoginHistory.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date,
            is_successful=True
        ).values('created_at__date').annotate(count=Count('id')).order_by('created_at__date')
        data = [{'date': str(l['created_at__date']), 'count': l['count']} for l in logins]
        return Response(data)





class CreateUserAPIView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            Wallet.objects.get_or_create(user=user)
        except OperationalError:
            return Response({'detail': 'Database connection error. Please try again later.'}, status=500)
        except Exception as e:
            print(f'[Registration] serializer_errors={serializer.errors if hasattr(serializer, "errors") else "N/A"}, error={type(e).__name__}: {e}')
            raise
        token = RefreshToken.for_user(user)
        verify_url = f"{request.data.get('frontend_url', 'http://localhost:5173')}/verify-email?token={str(token.access_token)}&email={user.email}"
        print(f'[RegistrationEmail] Attempting email to={user.email}, from={settings.DEFAULT_FROM_EMAIL}, backend={settings.EMAIL_BACKEND}')
        try:
            html_message = render_to_string('users/email_verification.html', {'verify_url': verify_url})
            text_message = render_to_string('users/email_verification.txt', {'verify_url': verify_url})
            email = EmailMessage(
                'UKGIN - Verify Your Email',
                text_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                headers={'Reply-To': settings.DEFAULT_FROM_EMAIL, 'X-Mailer': 'UKGIN'},
            )
            email.content_subtype = 'html'
            email.body = html_message
            email.send(fail_silently=False)
            print(f'[RegistrationEmail] Email sent successfully to={user.email}')
        except OperationalError:
            print('Registration DB error')
            return Response({'detail': 'Database connection error. Please try again later.'}, status=500)
        except Exception as e:
            print(f'[RegistrationEmail] FAILED email={user.email}, error={type(e).__name__}: {e}')
        return Response({'user': UserSerializer(user).data, 'detail': 'Registration successful. Please verify your email.'}, status=status.HTTP_201_CREATED)


class DeleteMyAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        user = request.user
        try:
            user.delete()
            return Response({'detail': 'Account deleted successfully'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'detail': f'Failed to delete account: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        users = User.objects.all()
        paginator = StandardPagination()
        page = paginator.paginate_queryset(users, request)
        if page is not None:
            serializer = UserSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = UserSerializer(users, many=True)
        return Response({'status': 'success', 'count': users.count(), 'data': serializer.data})


class UserDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        serializer = UserSerializer(user)
        return Response({'status': 'success', 'data': serializer.data})

    def put(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        serializer = UserSerializer(user, data=request.data, partial=False)
        if serializer.is_valid():
            if 'password' in request.data and request.data['password']:
                user.set_password(request.data['password'])
            updated_user = serializer.save()
            AuditLog.objects.create(
                admin_user=request.user,
                action='user_update',
                target_user=updated_user,
                details=f'User {updated_user.username} updated',
                ip_address=request.META.get('REMOTE_ADDR', ''),
            )
            return Response({'status': 'success', 'message': 'User updated', 'data': UserSerializer(updated_user).data})
        return Response({'status': 'error', 'errors': serializer.errors}, status=400)

    def patch(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            if 'password' in request.data and request.data['password']:
                user.set_password(request.data['password'])
            updated_user = serializer.save()
            AuditLog.objects.create(
                admin_user=request.user,
                action='user_update',
                target_user=updated_user,
                details=f'User {updated_user.username} updated',
                ip_address=request.META.get('REMOTE_ADDR', ''),
            )
            return Response({'status': 'success', 'message': 'User updated', 'data': UserSerializer(updated_user).data})
        return Response({'status': 'error', 'errors': serializer.errors}, status=400)

    def delete(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        username = user.username
        user.delete()
        AuditLog.objects.create(
            admin_user=request.user,
            action='user_delete',
            details=f'User {username} deleted',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )
        return Response({'status': 'success', 'message': f'User {username} deleted'}, status=204)


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        data = request.data
        if isinstance(data, str):
            import json
            try:
                data = json.loads(data)
            except Exception:
                data = {}
        email = data.get('email')
        if not email:
            return Response({'detail': 'Email is required'}, status=400)
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'detail': 'If that email exists, a password reset link has been sent.'})

        token = RefreshToken.for_user(user)
        reset_url = f"{request.data.get('frontend_url', 'http://localhost:5173')}/reset-password?token={str(token.access_token)}&email={user.email}"

        print(f'[PasswordReset] Attempting to send email to={user.email}, from={settings.DEFAULT_FROM_EMAIL}, backend={settings.EMAIL_BACKEND}, host={settings.EMAIL_HOST}:{settings.EMAIL_PORT}')
        try:
            html_message = render_to_string('users/password_reset.html', {'reset_url': reset_url})
            text_message = render_to_string('users/password_reset.txt', {'reset_url': reset_url})
            email = EmailMessage(
                'UKGIN Password Reset',
                text_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                headers={'Reply-To': settings.DEFAULT_FROM_EMAIL, 'X-Mailer': 'UKGIN'},
            )
            email.content_subtype = 'html'
            email.body = html_message
            email.send(fail_silently=False)
            print(f'[PasswordReset] Email sent successfully to={user.email}')
        except Exception as e:
            print(f'[PasswordReset] FAILED email={user.email}, error={type(e).__name__}: {e}')
            return Response({
                'detail': 'Password reset email could not be sent. Please check your email configuration or try again later.',
                'error': str(e),
                'error_type': type(e).__name__,
            }, status=500)

        AuditLog.objects.create(
            admin_user=user,
            action='user_reset_password',
            target_user=user,
            details=f'Password reset requested for {user.username}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )
        return Response({'detail': 'If that email exists, a password reset link has been sent.'})


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        data = request.data
        if isinstance(data, str):
            import json
            try:
                data = json.loads(data)
            except Exception:
                data = {}
        email = data.get('email')
        token = data.get('token')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')

        if not all([email, token, new_password, confirm_password]):
            return Response({'detail': 'All fields are required'}, status=400)
        if new_password != confirm_password:
            return Response({'detail': 'Passwords do not match'}, status=400)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'detail': 'Invalid request'}, status=400)

        user.set_password(new_password)
        user.save()

        AuditLog.objects.create(
            admin_user=user,
            action='user_reset_password',
            target_user=user,
            details=f'Password reset confirmed for {user.username}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )
        return Response({'detail': 'Password has been reset successfully'})


class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            user = serializer.save()
            return Response({'status': 'success', 'data': UserSerializer(user).data})
        return Response({'status': 'error', 'errors': serializer.errors}, status=400)


class AdminEventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all().order_by('-event_date')
    serializer_class = EventSerializer
    permission_classes = [IsAdminUser]


class AdminAnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.all().order_by('-created_at')
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class AdminDocumentCategoryViewSet(viewsets.ModelViewSet):
    queryset = DocumentCategory.objects.all().order_by('name')
    serializer_class = DocumentCategorySerializer
    permission_classes = [IsAdminUser]


class AdminDocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all().order_by('-created_at')
    serializer_class = DocumentSerializer
    permission_classes = [IsAdminUser]


class AdminConstitutionViewSet(viewsets.ModelViewSet):
    queryset = Constitution.objects.all().order_by('-effective_date', '-created_at')
    serializer_class = ConstitutionSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return self.queryset


class VolunteerApplicationViewSet(viewsets.ModelViewSet):
    queryset = VolunteerApplication.objects.all().order_by('-created_at')
    serializer_class = VolunteerApplicationSerializer
    permission_classes = [IsAdminUser]


class NewsletterSubscriptionViewSet(viewsets.ModelViewSet):
    queryset = NewsletterSubscription.objects.all().order_by('-created_at')
    serializer_class = NewsletterSubscriptionSerializer
    permission_classes = [IsAdminUser]

    @action(detail=False, methods=['post'])
    def subscribe(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'detail': 'Email is required'}, status=400)
        obj, created = NewsletterSubscription.objects.get_or_create(email=email)
        obj.is_subscribed = True
        obj.save()
        print(f'[NewsletterSubscribe] Attempting email to={email}, from={settings.DEFAULT_FROM_EMAIL}, backend={settings.EMAIL_BACKEND}')
        email_body = 'Thank you for subscribing to the UKGIN newsletter. You will now receive our latest updates and announcements.'
        print(f'[NewsletterSubscribe] Email content: to={email}, subject=UKGIN Newsletter Subscription Confirmed, body={email_body}')
        try:
            msg = EmailMessage(
                'UKGIN Newsletter Subscription Confirmed',
                email_body,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                headers={'Reply-To': settings.DEFAULT_FROM_EMAIL, 'X-Mailer': 'UKGIN'},
            )
            msg.content_subtype = 'html'
            msg.body = f'<html><body><p>{email_body}</p></body></html>'
            msg.send(fail_silently=False)
            print(f'[NewsletterSubscribe] Email sent successfully to={email}')
        except Exception as e:
            print(f'[NewsletterSubscribe] FAILED email={email}, error={type(e).__name__}: {e}')
            return Response({
                'detail': 'Subscription saved but confirmation email could not be sent. Please check your email configuration.',
                'error': str(e),
                'error_type': type(e).__name__,
            }, status=500)
        return Response({'detail': 'Subscribed successfully'})

    @action(detail=False, methods=['post'])
    def unsubscribe(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'detail': 'Email is required'}, status=400)
        try:
            obj = NewsletterSubscription.objects.get(email=email)
            obj.is_subscribed = False
            obj.save()
            return Response({'detail': 'Unsubscribed successfully'})
        except NewsletterSubscription.DoesNotExist:
            return Response({'detail': 'Email not found'}, status=404)


class NewsletterViewSet(viewsets.ModelViewSet):
    queryset = Newsletter.objects.all().order_by('-created_at')
    serializer_class = NewsletterSerializer
    permission_classes = [IsAdminUser]

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        newsletter = self.get_object()
        subscribers = NewsletterSubscription.objects.filter(is_subscribed=True)
        recipient_list = [sub.email for sub in subscribers]
        if not recipient_list:
            return Response({'detail': 'No subscribers found'}, status=400)
        try:
            send_mail(
                newsletter.subject,
                newsletter.message,
                settings.DEFAULT_FROM_EMAIL,
                recipient_list,
                fail_silently=False,
            )
            newsletter.sent_to_all = True
            newsletter.save()
            return Response({'detail': f'Newsletter sent to {len(recipient_list)} subscribers'})
        except Exception as e:
            return Response({'detail': f'Failed to send newsletter: {str(e)}'}, status=500)


class ContactMessageViewSet(viewsets.ModelViewSet):
    queryset = ContactMessage.objects.all().order_by('-created_at')
    serializer_class = ContactMessageSerializer
    permission_classes = [IsAdminUser]

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        was_responded = instance.responded
        response = super().partial_update(request, *args, **kwargs)
        updated_instance = self.get_object()
        if not was_responded and updated_instance.responded and updated_instance.response_text:
            try:
                send_mail(
                    f'UKGIN - Reply to your message: {updated_instance.subject}',
                    f'Dear {updated_instance.name},\n\nThank you for reaching out to us. Here is our response:\n\n{updated_instance.response_text}\n\nBest regards,\nUKGIN Team',
                    settings.DEFAULT_FROM_EMAIL,
                    [updated_instance.email],
                    fail_silently=True,
                )
            except Exception:
                pass
        return response


class PageContentViewSet(viewsets.ModelViewSet):
    queryset = PageContent.objects.all().order_by('title')
    serializer_class = PageContentSerializer
    permission_classes = [IsAdminUser]


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    permission_classes = [IsAdminUser]


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.select_related('author', 'category').all().order_by('-published_date', '-created_at')
    serializer_class = PostSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        qs = self.queryset
        if self.request.query_params.get('published') == 'true':
            qs = qs.filter(is_published=True)
        return qs


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.select_related('category').all().order_by('-created_at')
    serializer_class = ProjectSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        qs = self.queryset
        if self.request.query_params.get('active') == 'true':
            qs = qs.filter(is_active=True)
        return qs


class SocialMediaLinkViewSet(viewsets.ModelViewSet):
    queryset = SocialMediaLink.objects.all().order_by('order', 'name')
    serializer_class = SocialMediaLinkSerializer
    permission_classes = [IsAdminUser]


class GalleryImageViewSet(viewsets.ModelViewSet):
    queryset = GalleryImage.objects.all().order_by('order', '-created_at')
    serializer_class = GalleryImageSerializer
    permission_classes = [IsAdminUser]


class PartnerViewSet(viewsets.ModelViewSet):
    queryset = Partner.objects.all().order_by('order', '-created_at')
    serializer_class = PartnerSerializer
    permission_classes = [IsAdminUser]


class SponsorViewSet(viewsets.ModelViewSet):
    queryset = Sponsor.objects.all().order_by('order', '-created_at')
    serializer_class = SponsorSerializer
    permission_classes = [IsAdminUser]


class ExecutiveLeaderViewSet(viewsets.ModelViewSet):
    queryset = ExecutiveLeader.objects.all().order_by('order', 'name')
    serializer_class = ExecutiveLeaderSerializer
    permission_classes = [IsAdminUser]


class StateChapterViewSet(viewsets.ModelViewSet):
    queryset = StateChapter.objects.all().order_by('order', 'state')
    serializer_class = StateChapterSerializer
    permission_classes = [IsAdminUser]


class PublicEventsView(generics.ListAPIView):
    queryset = Event.objects.filter(is_past=False).order_by('event_date')
    serializer_class = EventSerializer
    permission_classes = [permissions.AllowAny]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class PublicConstitutionView(generics.ListAPIView):
    queryset = Constitution.objects.filter(is_current=True).order_by('-created_at')[:1]
    serializer_class = ConstitutionSerializer
    permission_classes = [permissions.AllowAny]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class PublicDocumentsView(generics.ListAPIView):
    queryset = Document.objects.filter(is_public=True).order_by('-created_at')
    serializer_class = DocumentSerializer
    permission_classes = [permissions.AllowAny]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class PublicDocumentCategoriesView(generics.ListAPIView):
    queryset = DocumentCategory.objects.all().order_by('name')
    serializer_class = DocumentCategorySerializer
    permission_classes = [permissions.AllowAny]


class PublicStateChaptersView(generics.ListAPIView):
    queryset = StateChapter.objects.filter(is_active=True).order_by('order', 'state')
    serializer_class = StateChapterSerializer
    permission_classes = [permissions.AllowAny]


class StateChapterMembersView(generics.ListAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = PublicUserSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        state = self.kwargs.get('state')
        return super().get_queryset().filter(state_of_residence__iexact=state)


class JoinChapterView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        state = request.data.get('state')
        if not state:
            return Response({'detail': 'State is required'}, status=400)
        chapter = get_object_or_404(StateChapter, state__iexact=state)
        user = request.user
        user.state_of_residence = chapter.state
        user.save()
        return Response({'detail': f'Joined {chapter.state} chapter successfully'})


class PublicEventResponseListView(generics.ListAPIView):
    queryset = EventResponse.objects.all().order_by('-created_at')
    serializer_class = PublicEventResponseSerializer
    permission_classes = [permissions.AllowAny]


class UserEventResponseCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        event_id = request.data.get('event')
        response_type = request.data.get('response_type')
        message = request.data.get('message', '')
        if not event_id or not response_type:
            return Response({'detail': 'Event and response_type are required'}, status=400)
        event = get_object_or_404(Event, id=event_id)
        obj, created = EventResponse.objects.get_or_create(
            event=event,
            user=request.user,
            defaults={'response_type': response_type, 'message': message},
        )
        if not created:
            obj.response_type = response_type
            obj.message = message
            obj.save()
        return Response({'detail': 'Response recorded', 'data': PublicEventResponseSerializer(obj).data})


class MyEventResponsesView(generics.ListAPIView):
    serializer_class = PublicEventResponseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return EventResponse.objects.filter(user=self.request.user).order_by('-created_at')


class AdminEventResponseViewSet(viewsets.ModelViewSet):
    queryset = EventResponse.objects.all().order_by('-created_at')
    serializer_class = PublicEventResponseSerializer
    permission_classes = [IsAdminUser]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = super().get_queryset()
        event_id = self.request.query_params.get('event_id')
        if event_id:
            qs = qs.filter(event_id=event_id)
        return qs


class EmailVerificationView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        token = request.query_params.get('token')
        email = request.query_params.get('email')
        if not token or not email:
            return Response({'detail': 'Token and email are required'}, status=400)
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'detail': 'Invalid request'}, status=400)
        if user.email_verified:
            return Response({'detail': 'Email already verified'})
        try:
            UntypedToken(token)
        except (InvalidToken, TokenError):
            return Response({'detail': 'Invalid or expired token'}, status=400)
        user.email_verified = True
        user.save()
        return Response({'detail': 'Email verified successfully'})


class ResendVerificationEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'detail': 'Email is required'}, status=400)
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'detail': 'No account found with this email.'}, status=404)
        if user.email_verified:
            return Response({'detail': 'Email is already verified. You can log in directly.'})
        try:
            token = RefreshToken.for_user(user)
            verification_url = f"{request.data.get('frontend_url', 'http://localhost:5173')}/verify-email?token={str(token.access_token)}&email={user.email}"
            send_mail(
                'UKGIN - Verify Your Email',
                f'Click the link to verify your email: {verification_url}',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            )
        except Exception:
            pass
        return Response({'detail': 'Verification email sent. Please check your inbox and spam/junk folder.'})


class PublicAnnouncementListView(generics.ListAPIView):
    queryset = Announcement.objects.filter(is_active=True).order_by('-created_at')
    serializer_class = PublicAnnouncementSerializer
    permission_classes = [permissions.AllowAny]


class MyNotificationsListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')


class UnreadNotificationCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({'unread_count': count})


class MarkNotificationReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk=None):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.is_read = True
        notification.save()
        return Response({'detail': 'Notification marked as read'})


class MarkAllNotificationsReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'detail': f'{count} notifications marked as read'})


class VolunteerApplicationCreateView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VolunteerApplicationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'detail': 'Application submitted successfully', 'data': serializer.data}, status=201)
        return Response({'status': 'error', 'errors': serializer.errors}, status=400)


class ContactMessageCreateView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ContactMessageSerializer(data=request.data)
        if serializer.is_valid():
            contact = serializer.save()
            try:
                send_mail(
                    'UKGIN - We Received Your Message',
                    f'Dear {contact.name},\n\nThank you for contacting UKGIN. We have received your message and our team will get back to you within 24-48 hours.\n\nSubject: {contact.subject}\nMessage: {contact.message}',
                    settings.DEFAULT_FROM_EMAIL,
                    [contact.email],
                    fail_silently=True,
                )
            except Exception:
                pass
            return Response({'detail': 'Message sent successfully', 'data': serializer.data}, status=201)
        return Response({'status': 'error', 'errors': serializer.errors}, status=400)


class PublicCategoryListView(generics.ListAPIView):
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class PublicPostListView(generics.ListAPIView):
    queryset = Post.objects.filter(is_published=True).order_by('-published_date')
    serializer_class = PostSerializer
    permission_classes = [permissions.AllowAny]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class PublicPostDetailView(generics.RetrieveAPIView):
    queryset = Post.objects.filter(is_published=True)
    serializer_class = PostSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class PublicProjectListView(generics.ListAPIView):
    queryset = Project.objects.filter(is_active=True).order_by('-created_at')
    serializer_class = ProjectSerializer
    permission_classes = [permissions.AllowAny]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class PublicProjectDetailView(generics.RetrieveAPIView):
    queryset = Project.objects.filter(is_active=True)
    serializer_class = ProjectSerializer
    permission_classes = [permissions.AllowAny]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class PublicSocialMediaLinksView(generics.ListAPIView):
    queryset = SocialMediaLink.objects.filter(is_active=True).order_by('order')
    serializer_class = SocialMediaLinkSerializer
    permission_classes = [permissions.AllowAny]


class PublicGalleryImageListView(generics.ListAPIView):
    queryset = GalleryImage.objects.filter(is_active=True).order_by('order')
    serializer_class = GalleryImageSerializer
    permission_classes = [permissions.AllowAny]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class PublicExecutiveLeadersView(generics.ListAPIView):
    queryset = ExecutiveLeader.objects.filter(is_active=True).order_by('order')
    serializer_class = ExecutiveLeaderSerializer
    permission_classes = [permissions.AllowAny]


class PublicPageContentView(generics.RetrieveAPIView):
    queryset = PageContent.objects.filter(is_published=True)
    serializer_class = PageContentSerializer
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        slug = self.kwargs.get('slug')
        return get_object_or_404(PageContent, slug=slug)


class ExportReportView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        report_type = request.query_params.get('type', 'daily')
        export_format = request.query_params.get('format', 'json')
        now = timezone.now()

        if report_type == 'daily':
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif report_type == 'weekly':
            start = now - timedelta(days=7)
        elif report_type == 'monthly':
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif report_type == 'yearly':
            start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start = now - timedelta(days=30)

        end_date = now

        data = {
            'report_type': report_type,
            'period': {'start': str(start), 'end': str(end_date)},
            'total_users': User.objects.filter(date_joined__gte=start, date_joined__lte=end_date).count(),
            'total_deposits': Deposit.objects.filter(created_at__gte=start, created_at__lte=end_date, status='approved').count(),
            'total_withdrawals': Withdrawal.objects.filter(created_at__gte=start, created_at__lte=end_date).count(),
            'total_donations': Donation.objects.filter(created_at__gte=start, created_at__lte=end_date, is_approved=True).count(),
            'total_revenue': float(Donation.objects.filter(created_at__gte=start, created_at__lte=end_date, is_approved=True).aggregate(total=Sum('amount'))['total'] or 0),
            'total_profit': float(Donation.objects.filter(created_at__gte=start, created_at__lte=end_date, is_approved=True).aggregate(total=Sum('amount'))['total'] or 0) - float(Withdrawal.objects.filter(created_at__gte=start, created_at__lte=end_date, status='approved').aggregate(total=Sum('amount'))['total'] or 0),
        }

        if export_format == 'csv':
            import csv
            from django.http import HttpResponse
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{report_type}_report.csv"'
            writer = csv.writer(response)
            writer.writerow(['Metric', 'Value'])
            for key, value in data.items():
                writer.writerow([key, value])
            return response

        return Response(data)