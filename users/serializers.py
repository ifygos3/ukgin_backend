from rest_framework import serializers
from .models import User, Wallet, WalletTransaction, KYCDocument, Donation, Deposit, Withdrawal, Notification, SupportTicket, TicketReply, Referral, AuditLog, SystemSettings, LoginHistory, Event, EventResponse, DocumentCategory, Document, Constitution


ROLE_CHOICES = [
    ('member', 'Member'),
    ('support_staff', 'Support Staff'),
    ('finance_manager', 'Finance Manager'),
    ('admin', 'Admin'),
    ('super_admin', 'Super Admin'),
]

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'phone_number', 'country', 'state_of_origin', 'lga', 'community', 'place_of_birth', 'sex', 'highest_qualification', 'institution_attended', 'year_of_graduation', 'profession', 'current_job', 'job_title', 'job_experience', 'current_employee', 'about_user', 'address', 'first_name', 'last_name', 'role', 'is_suspended', 'is_banned', 'kyc_status', 'total_donations', 'total_deposits', 'total_withdrawals', 'referred_by', 'referral_code', 'ip_address', 'device_info', 'last_login_ip', 'is_active', 'is_staff', 'date_joined', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'date_joined']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
            'username': {'required': False},
        }


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, default='strongpass123!')
    confirmPassword = serializers.CharField(write_only=True, required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    username = serializers.CharField(required=False)
    full_name = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    country = serializers.CharField(required=False, allow_blank=True)
    state_of_origin = serializers.CharField(required=False, allow_blank=True)
    lga = serializers.CharField(required=False, allow_blank=True)
    community = serializers.CharField(required=False, allow_blank=True)
    place_of_birth = serializers.CharField(required=False, allow_blank=True)
    sex = serializers.CharField(required=False, allow_blank=True)
    highest_qualification = serializers.CharField(required=False, allow_blank=True)
    institution_attended = serializers.CharField(required=False, allow_blank=True)
    year_of_graduation = serializers.CharField(required=False, allow_blank=True)
    profession = serializers.CharField(required=False, allow_blank=True)
    current_job = serializers.CharField(required=False, allow_blank=True)
    job_title = serializers.CharField(required=False, allow_blank=True)
    job_experience = serializers.CharField(required=False, allow_blank=True)
    current_employee = serializers.CharField(required=False, allow_blank=True)
    about_user = serializers.CharField(required=False, allow_blank=True)
    signature_data = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'confirmPassword', 'first_name', 'last_name', 'full_name', 'address', 'phone_number', 'country', 'state_of_origin', 'lga', 'community', 'place_of_birth', 'sex', 'highest_qualification', 'institution_attended', 'year_of_graduation', 'profession', 'current_job', 'job_title', 'job_experience', 'current_employee', 'about_user', 'signature_data']

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def validate(self, data):
        if data.get('confirmPassword') and data.get('password') and data['password'] != data['confirmPassword']:
            raise serializers.ValidationError({'confirmPassword': 'Passwords do not match.'})
        return data

    def create(self, validated_data):
        validated_data.pop('confirmPassword', None)
        signature_data = validated_data.pop('signature_data', None)
        password = validated_data.get('password', 'StrongPass123!')
        validated_data['password'] = password
        username = validated_data.get('username')
        if not username:
            username = validated_data.get('email', 'user').split('@')[0]
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        full_name = validated_data.pop('full_name', '')
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')
        if not first_name and not last_name and full_name:
            name_parts = full_name.strip().split(' ')
            first_name = name_parts[0] if name_parts else ''
            last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
        user = User.objects.create_user(
            username=username,
            email=validated_data.get('email'),
            password=validated_data['password'],
            first_name=first_name,
            last_name=last_name,
            full_name=full_name or f"{first_name} {last_name}".strip(),
        )
        for field in ['address', 'phone_number', 'country', 'state_of_origin', 'lga', 'community', 'place_of_birth', 'sex', 'highest_qualification', 'institution_attended', 'year_of_graduation', 'profession', 'current_job', 'job_title', 'job_experience', 'current_employee', 'about_user']:
            if field in validated_data:
                setattr(user, field, validated_data[field])
            elif field == 'about_user':
                setattr(user, field, '')
        user.save()
        if signature_data:
            import base64
            from django.core.files.base import ContentFile
            format, imgstr = signature_data.split(';base64,')
            ext = format.split('/')[-1]
            user.signature.save(f'signature_{user.id}.{ext}', ContentFile(base64.b64decode(imgstr)), save=True)
        return user


class WalletSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Wallet
        fields = ['id', 'user', 'balance', 'is_frozen', 'created_at', 'updated_at']


class WalletTransactionSerializer(serializers.ModelSerializer):
    wallet = WalletSerializer(read_only=True)

    class Meta:
        model = WalletTransaction
        fields = ['id', 'wallet', 'transaction_type', 'amount', 'description', 'reference', 'created_at']


class KYCDocumentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    document_file_url = serializers.SerializerMethodField()

    class Meta:
        model = KYCDocument
        fields = ['id', 'user', 'document_type', 'document_file', 'document_file_url', 'is_verified', 'verified_by', 'rejection_reason', 'created_at', 'updated_at']

    def get_document_file_url(self, obj):
        request = self.context.get('request')
        if obj.document_file and request:
            return request.build_absolute_uri(obj.document_file.url)
        return obj.document_file.url if obj.document_file else None


class DonationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    proof_of_donation_url = serializers.SerializerMethodField()

    class Meta:
        model = Donation
        fields = ['id', 'user', 'amount', 'payment_method', 'bank_name', 'account_number', 'crypto_type', 'wallet_address', 'card_type', 'card_last_four', 'card_holder', 'card_expiry', 'transaction_reference', 'proof_of_donation', 'proof_of_donation_url', 'notes', 'is_approved', 'approved_by', 'created_at', 'updated_at']

    def get_proof_of_donation_url(self, obj):
        request = self.context.get('request')
        if obj.proof_of_donation and request:
            return request.build_absolute_uri(obj.proof_of_donation.url)
        return obj.proof_of_donation.url if obj.proof_of_donation else None


class DepositSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    proof_of_payment_url = serializers.SerializerMethodField()

    class Meta:
        model = Deposit
        fields = ['id', 'user', 'amount', 'payment_method', 'bank_name', 'account_number', 'crypto_type', 'wallet_address', 'card_type', 'card_last_four', 'card_holder', 'card_expiry', 'transaction_reference', 'proof_of_payment', 'proof_of_payment_url', 'status', 'notes', 'approved_by', 'created_at', 'updated_at']

    def get_proof_of_payment_url(self, obj):
        request = self.context.get('request')
        if obj.proof_of_payment and request:
            return request.build_absolute_uri(obj.proof_of_payment.url)
        return obj.proof_of_payment.url if obj.proof_of_payment else None


class WithdrawalSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Withdrawal
        fields = ['id', 'user', 'amount', 'payment_method', 'bank_name', 'account_number', 'crypto_type', 'wallet_address', 'card_type', 'card_last_four', 'card_holder', 'card_expiry', 'transaction_reference', 'status', 'notes', 'processed_by', 'created_at', 'updated_at']


class NotificationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'user', 'title', 'message', 'notification_type', 'is_read', 'created_at']


class SupportTicketSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    assigned_to_user = UserSerializer(source='assigned_to', read_only=True)
    reply_count = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicket
        fields = ['id', 'user', 'subject', 'description', 'priority', 'status', 'assigned_to', 'assigned_to_user', 'reply_count', 'created_at', 'updated_at']

    def get_reply_count(self, obj):
        return obj.replies.count()


class TicketReplySerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = TicketReply
        fields = ['id', 'ticket', 'user', 'message', 'attachment', 'created_at']


class ReferralSerializer(serializers.ModelSerializer):
    referrer = UserSerializer(read_only=True)
    referee = UserSerializer(read_only=True)

    class Meta:
        model = Referral
        fields = ['id', 'referrer', 'referee', 'referral_code', 'status', 'reward_amount', 'completed_at', 'created_at']


class AuditLogSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'user', 'action', 'description', 'ip_address', 'device_info', 'metadata', 'created_at']


class SystemSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSettings
        fields = '__all__'


class LoginHistorySerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = LoginHistory
        fields = ['id', 'user', 'ip_address', 'device_info', 'location', 'is_successful', 'created_at']


class UserStatsSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    suspended_users = serializers.IntegerField()
    pending_kyc = serializers.IntegerField()
    approved_kyc = serializers.IntegerField()
    total_donations = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_deposits = serializers.DecimalField(max_digits=12, decimal_places=2)
    pending_deposits = serializers.DecimalField(max_digits=12, decimal_places=2)
    approved_deposits = serializers.DecimalField(max_digits=12, decimal_places=2)
    monthly_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_platform_balance = serializers.DecimalField(max_digits=12, decimal_places=2)


class DashboardStatsSerializer(UserStatsSerializer):
    pass


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'phone_number', 'address', 'country', 'state_of_origin', 'lga', 'community', 'role', 'kyc_status', 'signature', 'created_at']
        read_only_fields = ['id', 'created_at']


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    frontend_url = serializers.CharField(required=False, default='http://localhost:5173')


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    confirm_password = serializers.CharField(required=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return data


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'name', 'description', 'event_date', 'location', 'event_type', 'is_featured', 'is_past', 'created_at', 'updated_at']


class EventResponseSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    event_name = serializers.SerializerMethodField()

    class Meta:
        model = EventResponse
        fields = ['id', 'event', 'event_name', 'user', 'response_type', 'message', 'created_at']

    def get_event_name(self, obj):
        return obj.event.name if obj.event else ''


class DocumentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentCategory
        fields = ['id', 'name', 'slug', 'description', 'created_at', 'updated_at']


class DocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ['id', 'title', 'description', 'file', 'file_url', 'category', 'is_public', 'is_receipt', 'created_at', 'updated_at']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else None


class ConstitutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Constitution
        fields = ['id', 'version', 'title', 'content', 'file', 'is_current', 'effective_date', 'created_at', 'updated_at']