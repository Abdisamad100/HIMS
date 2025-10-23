from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.crypto import get_random_string
from django.dispatch import receiver
from django.db.models.signals import post_save
import uuid

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


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Automatically create or update Profile when User is saved."""
    if created:
        Profile.objects.create(user=instance)
    else:
        instance.profile.save()


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
            ('inactive', 'Inactive'),
            ('expired', 'Expired'),
        ],
        default='active'
    )
    created_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    def __str__(self):
        return f"{self.name} ({self.policy_number})"


# ==========================
#        MEMBER MODEL
# ==========================
class Member(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='member_profile')
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=255, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    registered_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registered_members',
        limit_choices_to={'profile__role': 'agent'}
    )

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.user.username})"

    def get_active_policies(self):
        """Return all active MemberPolicy records for this member."""
        return self.policies.filter(is_active=True)


# ==========================
#     MEMBER–POLICY LINK
# ==========================
class MemberPolicy(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='policies')
    policy = models.ForeignKey(Policy, on_delete=models.CASCADE, related_name='member_policies',null=True,blank=True,)
    member_policy_number = models.CharField(max_length=50, unique=True, blank=True)
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        """Auto-generate a unique member-policy number."""
        if not self.member_policy_number:
            self.member_policy_number = self.generate_policy_number()
        super().save(*args, **kwargs)

    def generate_policy_number(self):
        """Generate unique code like: POLI-0007-X7YZQ9"""
        prefix = self.policy.policy_number[:4].upper()
        unique_code = get_random_string(6).upper()
        member_id = str(self.member.id or 0).zfill(4)
        return f"{prefix}-{member_id}-{unique_code}"

    def __str__(self):
        return f"{self.member} → {self.policy} ({self.member_policy_number})"

    class Meta:
        unique_together = ('member', 'policy')
        verbose_name = "Member Policy"
        verbose_name_plural = "Member Policies"


# ==========================
#      MEMBER PAYMENT MODEL
# ==========================
class MemberPayment(models.Model):
    member_policy = models.ForeignKey(MemberPolicy, on_delete=models.CASCADE, related_name='payments',null=True,blank=True,)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField(auto_now_add=True)
    transaction_id = models.CharField(max_length=200, unique=True, default=uuid.uuid4)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def clean(self):
        """Ensure payment does not exceed policy premium."""
        total_paid = sum(p.amount for p in self.member_policy.payments.exclude(pk=self.pk))
        if total_paid + self.amount > self.member_policy.policy.premium:
            raise ValidationError("Total payments cannot exceed policy premium.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Payment {self.transaction_id} ({self.member_policy})"


# ==========================
#          CLAIM MODEL
# ==========================
class Claim(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Forwarded', 'Forwarded to Admin'),
        ('Reimbursed', 'Reimbursed'),
    ]

    member_policy = models.ForeignKey(MemberPolicy, on_delete=models.CASCADE, related_name='claims',null=True, blank=True,)
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

    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_claims')
    forwarded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='forwarded_claims')
    reimbursed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reimbursed_claims')

    reimbursed_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    reimbursed_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Claim #{self.id} ({self.member_policy})"

    # ======================
    #   VALIDATION LOGIC
    # ======================
    def clean(self):
        """Validate claim logic."""
        if not self.member_policy or not self.member_policy.policy:
            raise ValidationError("Invalid policy reference for this claim.")

        policy = self.member_policy.policy

        if policy.status != 'active':
            raise ValidationError("Cannot file a claim on an inactive or expired policy.")

        if self.amount <= 0:
            raise ValidationError("Claim amount must be greater than zero.")

        if self.date_of_service:
            if policy.start_date and self.date_of_service < policy.start_date:
                raise ValidationError("Claim date cannot be before policy start date.")
            if policy.end_date and self.date_of_service > policy.end_date:
                raise ValidationError("Claim date cannot be after policy end date.")

    @property
    def patient_name(self):
        """Return patient/member name."""
        if self.member_policy and self.member_policy.member:
            user = self.member_policy.member.user
            return user.get_full_name() or user.username
        return "Unknown"

    @property
    def policy_number(self):
        """Return related policy number."""
        if self.member_policy and self.member_policy.policy:
            return self.member_policy.policy.policy_number
        return "N/A"


# ==========================
#     CLAIM DOCUMENT MODEL
# ==========================
class ClaimDocument(models.Model):
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name="documents")
    document = models.FileField(upload_to="claims_docs/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document for {self.claim}"
