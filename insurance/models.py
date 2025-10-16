from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

# ==========================
#        POLICY MODEL
# ==========================
class Policy(models.Model):
    policy_number = models.CharField(max_length=120, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    premium = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('expired', 'Expired'),
            ('pending', 'Pending'),
        ],
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def total_members_premium(self):
        """Total premium expected from all members."""
        return sum(member.policy.premium for member in self.members.all() if member.policy)

    def total_paid_by_members(self):
        """Total payments made by all members for this policy."""
        return sum(payment.amount for payment in self.member_payments.all())

    def remaining_amount(self):
        """Total remaining premium to be paid by all members."""
        return self.total_members_premium() - self.total_paid_by_members()

    def __str__(self):
        return f"{self.policy_number} - {self.name}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Policies"


# ==========================
#        PROFILE MODEL
# ==========================
class Profile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('agent', 'Agent'),
        ('claim_officer', 'Claim Officer'),
        ('hospital', 'Hospital'),
        ('customer', 'Customer'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')

    def __str__(self):
        return f"{self.user.username} - {self.role}"


# ==========================
#        MEMBER MODEL
# ==========================
class Member(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='member_profile')
    registered_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registered_members',
        limit_choices_to={'profile__role': 'agent'}
    )
    policy = models.ForeignKey(
        Policy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members'
    )
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def total_premium_paid(self):
        """Total premium the member has paid."""
        return sum(payment.amount for payment in self.payments.all())  # payments → MemberPayment

    def remaining_premium(self):
        """Remaining premium for the member."""
        if self.policy:
            return self.policy.premium - self.total_premium_paid()
        return 0

    def __str__(self):
        return self.user.get_full_name() or self.user.username


# ==========================
#        CLAIM MODEL
# ==========================
class Claim(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Forwarded', 'Forwarded to Admin'),
        ('Reimbursed', 'Reimbursed'),
    ]
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='claims')
    hospital = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hospital_claims',
        limit_choices_to={'profile__role': 'hospital'}
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date_of_service = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_claims'
    )
    forwarded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='forwarded_claims'
    )
    reimbursed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reimbursed_claims'
    )
    reimbursed_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    reimbursed_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_reimbursed(self):
        return self.status == 'Reimbursed'

    def __str__(self):
        return f"Claim #{self.id} — {self.member.user.username} — {self.status}"


# ==========================
#        MEMBER PAYMENT MODEL
# ==========================
class MemberPayment(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='payments')
    policy = models.ForeignKey(Policy, on_delete=models.CASCADE, related_name='member_payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField(auto_now_add=True)
    transaction_id = models.CharField(max_length=200, unique=True)
    recorded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_member_payments'
    )

    def __str__(self):
        return f"MemberPayment {self.transaction_id} - {self.member.user.username}"

    class Meta:
        ordering = ['-payment_date']


# ==========================
#        HOSPITAL PAYMENT MODEL
# ==========================
class HospitalPayment(models.Model):
    claim = models.OneToOneField(Claim, on_delete=models.CASCADE, related_name='hospital_payment')
    hospital = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='hospital_payments',
        limit_choices_to={'profile__role': 'hospital'}
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_hospital_payments'
    )

    def __str__(self):
        return f"HospitalPayment for Claim #{self.claim.id} - {self.hospital.username}"

    class Meta:
        ordering = ['-payment_date']


# ==========================
#  AUTOMATIC CLAIM REIMBURSEMENT SIGNAL
# ==========================
@receiver(post_save, sender=Claim)
def auto_reimburse_claim(sender, instance, created, **kwargs):
    """
    Automatically create HospitalPayment when a claim is approved.
    """
    if instance.status == 'Approved' and not hasattr(instance, 'hospital_payment'):
        # Pick first admin if reimbursed_by not set
        if not instance.reimbursed_by:
            admin_user = User.objects.filter(profile__role='admin').first()
            instance.reimbursed_by = admin_user

        # Set reimbursed date
        instance.reimbursed_date = timezone.now()
        instance.status = 'Reimbursed'
        instance.save()

        # Create hospital payment
        HospitalPayment.objects.create(
            claim=instance,
            hospital=instance.hospital,
            amount=instance.amount,
            processed_by=instance.reimbursed_by
        )


# ==========================
#  CREATE PROFILE SIGNALS
# ==========================
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
