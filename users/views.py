from rest_framework import viewsets, permissions, status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action, api_view, permission_classes
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from .models import User, Wallet, WalletTransaction, KYCDocument, Donation, Deposit, Withdrawal, Notification, SupportTicket, TicketReply, Referral, AuditLog, SystemSettings, LoginHistory, Event, EventResponse, DocumentCategory, Document, Constitution, Announcement
from .serializers import (
    UserSerializer, RegisterSerializer, WalletSerializer, WalletTransactionSerializer,
    KYCDocumentSerializer, DonationSerializer, DepositSerializer, WithdrawalSerializer,
    NotificationSerializer, SupportTicketSerializer,
    TicketReplySerializer, ReferralSerializer, AuditLogSerializer, SystemSettingsSerializer,
    LoginHistorySerializer, DashboardStatsSerializer,
     EventSerializer, EventResponseSerializer, PublicEventResponseSerializer, DocumentCategorySerializer, DocumentSerializer, ConstitutionSerializer,
     AnnouncementSerializer, PublicAnnouncementSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
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
            return Response({'detail': 'Username, email, or phone number is required'}, status=400)
        if not password:
            return Response({'detail': 'Password is required'}, status=400)

        user = None
        if identifier:
            user = User.objects.filter(username=identifier).first()
            if not user:
                user = User.objects.filter(email=identifier).first()
            if not user:
                user = User.objects.filter(phone_number=identifier).first()

        if not user:
            AuditLog.objects.create(
                admin_user=None,
                action='login_failed',
                details=f'Failed login attempt for identifier: {identifier}',
                ip_address=request.META.get('REMOTE_ADDR', ''),
            )
            return Response({'detail': 'Invalid credentials'}, status=400)

        if not user.check_password(password):
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
            return Response({'detail': 'Invalid credentials'}, status=400)

        if user.is_suspended:
            return Response({'detail': 'Your account has been suspended. Please contact support.'}, status=403)
        if user.is_banned:
            return Response({'detail': 'Your account has been banned. Please contact support.'}, status=403)
        if not user.is_active:
            return Response({'detail': 'Your account has been deactivated. Please contact support.'}, status=403)

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
            permission_classes = [permissions.AllowAny]
        return [p() for p in permission_classes]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        Wallet.objects.get_or_create(user=user)
        Referral.objects.filter(referred_user=user).update(status='completed')
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
    def unban(self, request, pk=None):
        user = self.get_object()
        user.is_banned = False
        user.is_active = True
        user.is_suspended = False
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
    queryset = Notification.objects.all().order_by('-created_at')
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
    queryset = SupportTicket.objects.all().order_by('-created_at')
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
    queryset = AuditLog.objects.all().order_by('-created_at')
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
    queryset = LoginHistory.objects.all().order_by('-created_at')
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
        total_deposits = Deposit.objects.filter(status='approved').aggregate(total=Sum('amount'))['total'] or 0
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


class CreateUserAPIView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        Wallet.objects.get_or_create(user=user)
        return Response({'user': UserSerializer(user).data}, status=status.HTTP_201_CREATED)


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
        email = request.data.get('email')
        if not email:
            return Response({'detail': 'Email is required'}, status=400)
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'detail': 'If that email exists, a password reset link has been sent.'})

        token = RefreshToken.for_user(user)
        reset_url = f"{request.data.get('frontend_url', 'http://localhost:5173')}/reset-password?token={str(token.access_token)}&email={user.email}"

        try:
            send_mail(
                'UKGIN Password Reset',
                f'Click the link to reset your password: {reset_url}',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
        except Exception:
            pass

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
        email = request.data.get('email')
        token = request.data.get('token')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

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


class PublicEventsView(generics.ListAPIView):
    queryset = Event.objects.all().order_by('-event_date')
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


class AdminEventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all().order_by('-event_date')
    serializer_class = EventSerializer
    permission_classes = [IsAdminUser]


class AdminEventResponseViewSet(viewsets.ModelViewSet):
    queryset = EventResponse.objects.all().order_by('-created_at')
    serializer_class = EventResponseSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        event_id = self.request.query_params.get('event_id')
        user_id = self.request.query_params.get('user_id')
        qs = self.queryset
        if event_id:
            qs = qs.filter(event_id=event_id)
        if user_id:
            qs = qs.filter(user_id=user_id)
        return qs


class PublicEventResponseListView(generics.ListAPIView):
    serializer_class = PublicEventResponseSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        event_id = self.request.query_params.get('event_id')
        if event_id:
            return EventResponse.objects.filter(event_id=event_id).order_by('-created_at')
        return EventResponse.objects.none()


class UserEventResponseCreateView(generics.CreateAPIView):
    serializer_class = EventResponseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        event_id = self.request.data.get('event')
        response_type = self.request.data.get('response_type')
        message = self.request.data.get('message', '')
        event = get_object_or_404(Event, id=event_id)
        existing = EventResponse.objects.filter(event=event, user=self.request.user).first()
        if existing:
            existing.response_type = response_type
            existing.message = message
            existing.save()
            serializer.instance = existing
        else:
            serializer.save(user=self.request.user, event=event)


class MyEventResponsesView(generics.ListAPIView):
    serializer_class = EventResponseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return EventResponse.objects.filter(user=self.request.user).order_by('-created_at')


class AdminDocumentCategoryViewSet(viewsets.ModelViewSet):
    queryset = DocumentCategory.objects.all().order_by('name')
    serializer_class = DocumentCategorySerializer
    permission_classes = [IsAdminUser]


class AdminDocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all().order_by('-created_at')
    serializer_class = DocumentSerializer
    permission_classes = [IsAdminUser]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class AdminConstitutionViewSet(viewsets.ModelViewSet):
    queryset = Constitution.objects.all().order_by('-created_at')
    serializer_class = ConstitutionSerializer
    permission_classes = [IsAdminUser]


class PublicStateChaptersView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        states = User.objects.values_list('state_of_origin', flat=True).distinct().exclude(state_of_origin='').exclude(state_of_origin__isnull=True)
        chapters = []
        for state in states:
            count = User.objects.filter(state_of_origin=state).count()
            chapters.append({
                'state': state,
                'members': count,
            })
        chapters.sort(key=lambda x: x['state'])
        return Response(chapters)


class StateChapterMembersView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, state):
        members = User.objects.filter(state_of_origin=state)
        data = UserProfileSerializer(members, many=True).data
        return Response(data)


class JoinChapterView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        state = request.data.get('state')
        if not state:
            return Response({'detail': 'State is required'}, status=status.HTTP_400_BAD_REQUEST)
        request.user.state_of_origin = state
        request.user.save()
        return Response({'status': 'success', 'message': f'Joined {state} chapter', 'state': state})


class AdminAnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.all().order_by('-created_at')
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class PublicAnnouncementListView(generics.ListAPIView):
    serializer_class = PublicAnnouncementSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Announcement.objects.filter(is_active=True).order_by('-created_at')[:10]