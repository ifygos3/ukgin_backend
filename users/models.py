from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from .storage import DatabaseFileStorage

PAYMENT_METHODS = [
    ('bank_transfer', 'Bank Transfer'),
    ('crypto', 'Cryptocurrency'),
    ('other', 'Other'),
]

DEPOSIT_STATUS = [
    ('pending', 'Pending'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
]

WITHDRAWAL_STATUS = [
    ('pending', 'Pending'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('processing', 'Processing'),
    ('completed', 'Completed'),
]

DOCUMENT_TYPES = [
    ('id_card', 'ID Card'),
    ('passport', 'Passport'),
    ('selfie', 'Selfie'),
]

KYC_STATUS = [
    ('pending', 'Pending'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('resubmission', 'Resubmission Requested'),
]

TRANSACTION_TYPES = [
    ('credit', 'Credit'),
    ('debit', 'Debit'),
]

NOTIFICATION_TYPES = [
    ('announcement', 'Announcement'),
    ('email', 'Email'),
    ('in_app', 'In-App'),
    ('maintenance', 'Maintenance'),
]

PRIORITY_CHOICES = [
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
    ('urgent', 'Urgent'),
]

TICKET_STATUS = [
    ('open', 'Open'),
    ('in_progress', 'In Progress'),
    ('closed', 'Closed'),
    ('reopened', 'Reopened'),
]

REFERRAL_STATUS = [
    ('pending', 'Pending'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
]

INVESTMENT_STATUS = [
    ('active', 'Active'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
]

AUDIT_ACTIONS = [
    ('login', 'Login'),
    ('login_failed', 'Login Failed'),
    ('logout', 'Logout'),
    ('user_create', 'User Created'),
    ('user_update', 'User Updated'),
    ('user_delete', 'User Deleted'),
    ('user_activate', 'User Activated'),
    ('user_suspend', 'User Suspended'),
    ('user_ban', 'User Banned'),
    ('user_reset_password', 'User Password Reset'),
    ('user_role_change', 'User Role Changed'),
    ('deposit_approve', 'Deposit Approved'),
    ('deposit_reject', 'Deposit Rejected'),
    ('withdrawal_approve', 'Withdrawal Approved'),
    ('withdrawal_reject', 'Withdrawal Rejected'),
    ('kyc_approve', 'KYC Approved'),
    ('kyc_reject', 'KYC Rejected'),
    ('wallet_credit', 'Wallet Credited'),
    ('wallet_debit', 'Wallet Debited'),
    ('wallet_freeze', 'Wallet Frozen'),
    ('wallet_unfreeze', 'Wallet Unfrozen'),
    ('donation_approve', 'Donation Approved'),
    ('notification_send', 'Notification Sent'),
    ('ticket_assign', 'Ticket Assigned'),
    ('ticket_close', 'Ticket Closed'),
    ('ticket_reopen', 'Ticket Reopened'),
    ('settings_update', 'Settings Updated'),
    ('report_generated', 'Report Generated'),
    ('other', 'Other'),
]

ROLE_CHOICES = [
    ('member', 'Member'),
    ('support_staff', 'Support Staff'),
    ('finance_manager', 'Finance Manager'),
    ('admin', 'Admin'),
    ('super_admin', 'Super Admin'),
]


class User(AbstractUser):
    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    address = models.CharField(max_length=300)
    phone_number = models.CharField(max_length=20)
    country = models.CharField(max_length=50)
    state_of_origin = models.CharField(max_length=50)
    state_of_residence = models.CharField(max_length=100, null=True, blank=True)
    lga = models.CharField(max_length=50)
    community = models.CharField(max_length=100, null=True, blank=True)
    place_of_birth = models.CharField(max_length=100)
    sex = models.CharField(max_length=10)
    highest_qualification = models.CharField(max_length=100)
    institution_attended = models.CharField(max_length=100)
    year_of_graduation = models.CharField(max_length=100)
    profession = models.CharField(max_length=100)
    current_job = models.CharField(max_length=100)
    job_title = models.CharField(max_length=100)
    job_experience = models.CharField(max_length=1000)
    current_employee = models.CharField(max_length=100)
    about_user = models.TextField(null=True, blank=True)
    role = models.CharField(
        max_length=20,
        choices=[
            ('member', 'Member'),
            ('support_staff', 'Support Staff'),
            ('finance_manager', 'Finance Manager'),
            ('admin', 'Admin'),
            ('super_admin', 'Super Admin'),
        ],
        default='member',
    )
    is_suspended = models.BooleanField(default=False)
    is_banned = models.BooleanField(default=False)
    kyc_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('resubmission', 'Resubmission Requested'),
        ],
        default='pending',
    )
    total_donations = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deposits = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_withdrawals = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    referred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referrals',
    )
    referral_code = models.CharField(max_length=20, unique=True, null=True, blank=True)
    ip_address = models.CharField(max_length=45, null=True, blank=True)
    device_info = models.CharField(max_length=200, null=True, blank=True)
    last_login_ip = models.CharField(max_length=45, null=True, blank=True)
    signature = models.ImageField(upload_to='signatures/', null=True, blank=True)
    signature_data = models.TextField(blank=True)
    email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name


class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallet',
    )
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_frozen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet of {self.user.full_name}"


class WalletTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    ]
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='transactions',
    )
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True)
    reference = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} - {self.reference}"


class KYCDocument(models.Model):
    DOCUMENT_TYPES = [
        ('id_card', 'ID Card'),
        ('passport', 'Passport'),
        ('selfie', 'Selfie'),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='kyc_documents',
    )
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    document_file = models.FileField(upload_to='kyc_documents/')
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_kyc',
    )
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.document_type} - {self.user.full_name}"


class Donation(models.Model):
    PAYMENT_METHODS = [
        ('bank_transfer', 'Bank Transfer'),
        ('crypto', 'Cryptocurrency'),
        ('other', 'Other'),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='donations',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=30, blank=True)
    crypto_type = models.CharField(max_length=50, blank=True)
    wallet_address = models.CharField(max_length=200, blank=True)
    proof_of_donation = models.FileField(upload_to='donation_proofs/', blank=True, null=True)
    notes = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_donations',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Donation of {self.amount} by {self.user.full_name}"


class Deposit(models.Model):
    PAYMENT_METHODS = [
        ('bank_transfer', 'Bank Transfer'),
        ('crypto', 'Cryptocurrency'),
        ('other', 'Other'),
    ]
    DEPOSIT_STATUS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='deposits',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=30, blank=True)
    crypto_type = models.CharField(max_length=50, blank=True)
    wallet_address = models.CharField(max_length=200, blank=True)
    proof_of_payment = models.FileField(upload_to='deposit_proofs/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=DEPOSIT_STATUS, default='pending')
    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_deposits',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Deposit of {self.amount} - {self.status} by {self.user.full_name}"


class Withdrawal(models.Model):
    WITHDRAWAL_STATUS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='withdrawals',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=30, blank=True)
    crypto_type = models.CharField(max_length=50, blank=True)
    wallet_address = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=WITHDRAWAL_STATUS, default='pending')
    notes = models.TextField(blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_withdrawals',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Withdrawal of {self.amount} - {self.status} by {self.user.full_name}"



class LoginHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='login_history',
    )
    ip_address = models.CharField(max_length=45)
    device_info = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=200, blank=True)
    is_successful = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Login by {self.user.full_name} at {self.created_at}"


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('announcement', 'Announcement'),
        ('email', 'Email'),
        ('in_app', 'In-App'),
        ('maintenance', 'Maintenance'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='in_app')
    sent_to_all = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_notifications',
        null=True,
        blank=True,
    )
    target_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='targeted_notifications')
    announcement = models.ForeignKey(
        'Announcement',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class SupportTicket(models.Model):
    TICKET_STATUS = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('closed', 'Closed'),
        ('reopened', 'Reopened'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    subject = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=TICKET_STATUS, default='open')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='support_tickets',
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets',
    )
    attachment = models.FileField(upload_to='ticket_attachments/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} - {self.user.full_name}"


class TicketReply(models.Model):
    message = models.TextField()
    attachment = models.FileField(upload_to='ticket_replies/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name='replies',
    )

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Reply to {self.ticket.subject}"


class Referral(models.Model):
    REFERRAL_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    reward_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=REFERRAL_STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    referred_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referral_referred_users',
    )
    referrer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referral_referrers',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Referral by {self.referrer.full_name}"


class AuditLog(models.Model):
    AUDIT_ACTIONS = [
        ('login', 'Login'),
        ('login_failed', 'Login Failed'),
        ('logout', 'Logout'),
        ('user_create', 'User Created'),
        ('user_update', 'User Updated'),
        ('user_delete', 'User Deleted'),
        ('user_activate', 'User Activated'),
        ('user_suspend', 'User Suspended'),
        ('user_ban', 'User Banned'),
        ('user_reset_password', 'User Password Reset'),
        ('user_role_change', 'User Role Changed'),
        ('deposit_approve', 'Deposit Approved'),
        ('deposit_reject', 'Deposit Rejected'),
        ('withdrawal_approve', 'Withdrawal Approved'),
        ('withdrawal_reject', 'Withdrawal Rejected'),
        ('kyc_approve', 'KYC Approved'),
        ('kyc_reject', 'KYC Rejected'),
        ('wallet_credit', 'Wallet Credited'),
        ('wallet_debit', 'Wallet Debited'),
        ('wallet_freeze', 'Wallet Frozen'),
        ('wallet_unfreeze', 'Wallet Unfrozen'),
        ('donation_approve', 'Donation Approved'),
        ('notification_send', 'Notification Sent'),
        ('ticket_assign', 'Ticket Assigned'),
        ('ticket_close', 'Ticket Closed'),
        ('ticket_reopen', 'Ticket Reopened'),
        ('settings_update', 'Settings Updated'),
        ('report_generated', 'Report Generated'),
        ('other', 'Other'),
    ]
    action = models.CharField(max_length=30, choices=AUDIT_ACTIONS)
    details = models.TextField()
    ip_address = models.CharField(max_length=45)
    created_at = models.DateTimeField(auto_now_add=True)
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='admin_audit_logs',
        null=True,
        blank=True,
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='target_audit_logs',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} by {self.admin_user.full_name}"


class SystemSettings(models.Model):
    site_name = models.CharField(max_length=200, default='UKGIN')
    logo = models.ImageField(upload_to='settings/', blank=True, null=True)
    favicon = models.ImageField(upload_to='settings/', blank=True, null=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_address = models.TextField(blank=True)
    email_host = models.CharField(max_length=200, blank=True)
    email_port = models.IntegerField(default=587)
    email_host_user = models.CharField(max_length=200, blank=True)
    email_host_password = models.CharField(max_length=200, blank=True)
    sms_api_key = models.CharField(max_length=200, blank=True)
    sms_api_secret = models.CharField(max_length=200, blank=True)
    payment_wallet_address = models.CharField(max_length=200, blank=True)
    crypto_wallet_address = models.CharField(max_length=200, blank=True)
    supported_cryptocurrencies = models.TextField(blank=True)
    minimum_deposit = models.DecimalField(decimal_places=2, default=10, max_digits=12)
    maximum_deposit = models.DecimalField(decimal_places=2, default=10000, max_digits=12)
    maintenance_mode = models.BooleanField(default=False)
    terms_and_conditions = models.TextField(blank=True)
    privacy_policy = models.TextField(blank=True)
    bank_name = models.CharField(max_length=200, blank=True)
    account_name = models.CharField(max_length=200, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    btc_address = models.CharField(max_length=200, blank=True)
    eth_address = models.CharField(max_length=200, blank=True)
    usdt_address = models.CharField(max_length=200, blank=True)
    bnb_address = models.CharField(max_length=200, blank=True)
    sol_address = models.CharField(max_length=200, blank=True)
    card_payment_enabled = models.BooleanField(default=True)
    card_payment_provider = models.CharField(max_length=100, blank=True)
    card_api_key = models.CharField(max_length=200, blank=True)
    card_api_secret = models.CharField(max_length=200, blank=True)
    roi_percentage = models.DecimalField(decimal_places=2, default=5, max_digits=5)
    investment_duration_days = models.IntegerField(default=30)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'System Settings'

    def __str__(self):
        return self.site_name


class Investment(models.Model):
    INVESTMENT_STATUS = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='investments',
    )
    plan_name = models.CharField(max_length=100)
    roi_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    investment_duration_days = models.IntegerField()
    amount_invested = models.DecimalField(max_digits=12, decimal_places=2)
    expected_return = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=INVESTMENT_STATUS, default='active')
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.plan_name} - {self.user.full_name}"


class Event(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    event_date = models.DateTimeField()
    location = models.CharField(max_length=200)
    event_type = models.CharField(max_length=100)
    is_featured = models.BooleanField(default=False)
    is_past = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-event_date']

    def __str__(self):
        return self.name


class Announcement(models.Model):
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_active = models.BooleanField(default=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='announcements',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class EventResponse(models.Model):
    RESPONSE_TYPES = [
        ('going', 'Going'),
        ('interested', 'Interested'),
        ('not_going', 'Not Going'),
    ]
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='responses',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='event_responses',
    )
    response_type = models.CharField(max_length=20, choices=RESPONSE_TYPES)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['event', 'user']

    def __str__(self):
        return f"{self.user.full_name} - {self.response_type} - {self.event.name}"


class DocumentCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Document Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Document(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='documents/')
    category = models.ForeignKey(
        DocumentCategory,
        on_delete=models.CASCADE,
        related_name='documents',
    )
    is_public = models.BooleanField(default=True)
    is_receipt = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class DocumentBlob(models.Model):
    """File bytes kept in Postgres so uploads survive container redeploys."""

    name = models.CharField(max_length=500, unique=True)
    data = models.BinaryField()
    content_type = models.CharField(max_length=150, default='application/octet-stream')
    size = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Document blobs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.size} bytes)"


class Constitution(models.Model):
    version = models.CharField(max_length=20)
    title = models.CharField(max_length=200)
    content = models.TextField()
    file = models.FileField(upload_to='constitutions/', storage=DatabaseFileStorage(), blank=True, null=True)
    is_current = models.BooleanField(default=False)
    effective_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-effective_date', '-created_at']

    def __str__(self):
        return f"{self.title} - {self.version}"

    def save(self, *args, **kwargs):
        # Only one constitution can be the public one, whichever panel saved it.
        if self.is_current:
            Constitution.objects.exclude(pk=self.pk).filter(is_current=True).update(is_current=False)
        previous_file = None
        if self.pk:
            previous_file = (
                Constitution.objects.filter(pk=self.pk)
                .values_list('file', flat=True)
                .first()
            )
        super().save(*args, **kwargs)
        # Replacing a PDF leaves the old bytes behind in the blob table; drop them.
        if previous_file and previous_file != self.file.name:
            DocumentBlob.objects.filter(name=previous_file.replace('\\', '/')).delete()

    def delete(self, *args, **kwargs):
        stored_name = self.file.name if self.file else None
        result = super().delete(*args, **kwargs)
        if stored_name:
            DocumentBlob.objects.filter(name=stored_name.replace('\\', '/')).delete()
        return result


class VolunteerApplication(models.Model):
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20, blank=True)
    skills = models.TextField(blank=True, help_text="e.g., Event Planning, Writing, Design")
    availability = models.CharField(max_length=20, choices=[
        ('weekdays', 'Weekdays'),
        ('weekends', 'Weekends'),
        ('flexible', 'Flexible'),
    ], blank=True)
    areas_of_interest = models.TextField(blank=True, help_text="Comma-separated values")
    resume = models.FileField(upload_to='volunteer_resumes/', blank=True, null=True)
    is_reviewed = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending Review'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ], default='pending')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} - {self.email}"


class NewsletterSubscription(models.Model):
    email = models.EmailField(unique=True)
    is_subscribed = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.email


class Newsletter(models.Model):
    subject = models.CharField(max_length=200)
    message = models.TextField()
    sent_to_all = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.subject


class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    responded = models.BooleanField(default=False)
    response_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} - {self.name}"


class PageContent(models.Model):
    PAGE_TYPES = [
        ('about', 'About Us'),
        ('organizational_structure', 'Organizational Structure'),
        ('state_chapters', 'State Chapters'),
        ('achievements', 'Achievements'),
        ('executive_leadership', 'Executive Leadership'),
        ('constitution', 'Constitution'),
        ('refund_policy', 'Refund Policy'),
        ('privacy_policy', 'Privacy Policy'),
        ('terms_conditions', 'Terms & Conditions'),
        ('cookie_policy', 'Cookie Policy'),
        ('mission_vision', 'Mission & Vision'),
    ]
    slug = models.SlugField(max_length=100, unique=True)
    page_type = models.CharField(max_length=50, choices=PAGE_TYPES, unique=True, blank=True, null=True)
    title = models.CharField(max_length=200)
    meta_title = models.CharField(max_length=200, blank=True, default='')
    meta_description = models.CharField(max_length=500, blank=True, default='')
    content = models.TextField()
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


class Post(models.Model):
    POST_TYPES = [
        ('news', 'News'),
        ('blog', 'Blog'),
    ]
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    excerpt = models.TextField(blank=True, help_text="Short summary of the post")
    content = models.TextField()
    post_type = models.CharField(max_length=10, choices=POST_TYPES, default='news')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posts',
    )
    author_name = models.CharField(max_length=100, blank=True, help_text="Display name if no user author")
    image = models.ImageField(upload_to='post_images/', blank=True, null=True)
    is_published = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    published_date = models.DateTimeField(null=True, blank=True)
    view_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_date', '-created_at']

    def __str__(self):
        return self.title

    @property
    def author_display(self):
        if self.author:
            return self.author.full_name or self.author.username
        return self.author_name or 'Admin'


class Project(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(help_text="Short description for listing")
    content = models.TextField(help_text="Full project description")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='projects')
    image = models.ImageField(upload_to='project_images/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class SocialMediaLink(models.Model):
    SOCIAL_CHOICES = [
        ('facebook', 'Facebook'),
        ('twitter', 'Twitter'),
        ('instagram', 'Instagram'),
        ('linkedin', 'LinkedIn'),
        ('youtube', 'YouTube'),
        ('tiktok', 'TikTok'),
        ('whatsapp', 'WhatsApp'),
        ('telegram', 'Telegram'),
        ('github', 'GitHub'),
        ('other', 'Other'),
    ]
    name = models.CharField(max_length=100, choices=SOCIAL_CHOICES)
    url = models.URLField(max_length=200)
    icon_class = models.CharField(max_length=100, default='social-icon', help_text="CSS class for the icon")
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0, help_text="Display order")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.get_name_display()


class ExecutiveLeader(models.Model):
    name = models.CharField(max_length=100)
    position = models.CharField(max_length=100)
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to='leadership_photos/', blank=True, null=True)
    years_in_office = models.CharField(max_length=100, blank=True, help_text="e.g., '2020-present'")
    email = models.EmailField(blank=True)
    order = models.IntegerField(default=0, help_text="Display order")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.name} - {self.position}"


class StateChapter(models.Model):
    state = models.CharField(max_length=100, unique=True)
    coordinator = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'state']

    def __str__(self):
        return self.state


class GalleryImage(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    image = models.FileField(upload_to='gallery_media/', blank=True, null=True)
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES, default='image')
    youtube_url = models.URLField(max_length=300, blank=True, null=True, help_text='YouTube video URL for video gallery items.')
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.webm', '.mkv', '.ogg', '.ogv', '.flv', '.wmv']

    class Meta:
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title or f"Gallery Image {self.id}"

    def is_video(self):
        if self.media_type == 'video':
            return True
        if self.youtube_url:
            return True
        if not self.image or not self.image.name:
            return False
        try:
            name = self.image.name.lower()
            if any(name.endswith(ext) for ext in self.VIDEO_EXTENSIONS):
                return True
            url = self.image.url.lower()
            if '/video/upload/' in url:
                return True
        except Exception:
            pass
        return False

    def save(self, *args, **kwargs):
        if self.image and not self.youtube_url:
            detected = 'video' if self.is_video() else 'image'
            if self.media_type != detected:
                self.media_type = detected
        super().save(*args, **kwargs)


class Partner(models.Model):
    name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to='partners/', blank=True, null=True)
    website = models.URLField(blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.name


class Sponsor(models.Model):
    name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to='sponsors/', blank=True, null=True)
    website = models.URLField(blank=True)
    description = models.TextField(blank=True)
    tier = models.CharField(max_length=20, choices=[('gold', 'Gold'), ('silver', 'Silver'), ('bronze', 'Bronze'), ('platinum', 'Platinum')], default='bronze')
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.name