from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.generic import ListView, DetailView
from .models import Claim, Member
from .forms import ClaimForm
from django.db.models import Sum


from .forms import (
    UserRegistrationForm,
    ProfileForm,
    MemberRegistrationForm,
)
from .models import Profile, Member


# ==========================
#        ROLE HELPERS
# ==========================

def is_admin(user):
    return hasattr(user, 'profile') and user.profile.role == 'admin'


def is_agent(user):
    return hasattr(user, 'profile') and user.profile.role == 'agent'


# ==========================
#     ADMIN REGISTRATION
# ==========================

@login_required
@user_passes_test(is_admin)
def register_user(request):
    """
    Admin can create users for roles:
    - Agent
    - Claim Officer
    - Hospital
    """
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        profile_form = ProfileForm(request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            # --- Create new user ---
            user = user_form.save(commit=False)
            user.set_password(user_form.cleaned_data['password'])
            user.save()

            # --- Get the auto-created profile and set role ---
            profile = user.profile  # ✅ already created by signal
            profile.role = profile_form.cleaned_data['role']
            profile.save()

            messages.success(
                request,
                f"{profile.get_role_display()} account created successfully!"
            )
            return redirect('admin_dashboard')

        messages.error(request, "Please correct the errors below.")
    else:
        user_form = UserRegistrationForm()
        profile_form = ProfileForm()

    return render(request, 'registration/register_user.html', {
        'user_form': user_form,
        'profile_form': profile_form,
    })
# ==========================
#     AGENT REGISTRATION
# ==========================

@login_required
@user_passes_test(is_agent)
def register_member(request):
    """
    Agents can register new customers (members).
    Automatically assigns:
    - Profile(role='customer')
    - Member(registered_by=agent_user)
    """
    if request.method == 'POST':
        form = MemberRegistrationForm(request.POST)
        if form.is_valid():
            # --- Create the User for the new member ---
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password']
            )

            # --- Assign customer role ---
            profile = user.profile
            profile.role = 'customer'
            profile.save()

            # --- Create Member record linked to agent ---
            member = form.save(commit=False)
            member.user = user
            member.registered_by = request.user
            member.save()

            messages.success(
                request,
                f"Member '{user.get_full_name() or user.username}' registered successfully ✅"
            )
            return redirect('member_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = MemberRegistrationForm()

    return render(request, 'registration/register_member.html', {'form': form})


# ==========================
#        MEMBER LIST
# ==========================

@login_required
def member_list(request):
    """
    Displays members depending on the user's role:
    - Agent: sees only their own registered members
    - Admin/Claim Officer: sees all members
    - Customer/Hospital: limited or denied
    """
    role = getattr(request.user.profile, 'role', None)

    if role == 'agent':
        members = Member.objects.filter(registered_by=request.user)
    elif role in ['admin', 'claim_officer']:
        members = Member.objects.all()
    else:
        messages.error(request, "Access denied.")
        return redirect('home')

    return render(request, 'members/member_list.html', {'members': members})



from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Profile, Member, Policy, Claim


@login_required
def dashboard(request):
    """Redirect users to their role-based dashboard."""
    role = request.user.profile.role

    if role == 'admin':
        return redirect('admin_dashboard')
    elif role == 'agent':
        return redirect('agent_dashboard')
    elif role == 'claim_officer':
        return redirect('claim_dashboard')
    elif role == 'hospital':
        return redirect('hospital_dashboard')
    else:
        return redirect('customer_dashboard')


# --- Admin Dashboard ---

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from .models import Profile, Policy, Claim, Member

# -------------------
# Admin Dashboard
# -------------------
@login_required
def admin_dashboard(request):
    """Admin sees all users, hospitals, agents, and claims."""
    if request.user.profile.role != "admin":
        messages.error(request, "Access denied.")
        return redirect('claim_dashboard')  # redirect non-admin users

    users_count = Profile.objects.count()
    policies_count = Policy.objects.count()
    claims_count = Claim.objects.count()
    agents_count = Profile.objects.filter(role='agent').count()
    hospitals_count = Profile.objects.filter(role='hospital').count()

    # Recent users and claims
    recent_users = Profile.objects.select_related('user').order_by('-user__date_joined')[:5]
    recent_claims = Claim.objects.select_related('member', 'hospital').order_by('-created_at')[:5]

    # Claims summary
    claims_pending = Claim.objects.filter(status='Pending').count()
    claims_approved = Claim.objects.filter(status='Approved').count()
    claims_rejected = Claim.objects.filter(status='Rejected').count()

    context = {
        'users_count': users_count,
        'policies': policies_count,
        'claims': claims_count,
        'agents': agents_count,
        'hospitals': hospitals_count,
        'recent_users': recent_users,
        'recent_claims': recent_claims,
        'claims_pending': claims_pending,
        'claims_approved': claims_approved,
        'claims_rejected': claims_rejected,
        'users': Profile.objects.select_related('user').exclude(role__in=['agent', 'hospital']),
        'agent_list': Profile.objects.filter(role='agent').select_related('user'),
        'hospital_list': Profile.objects.filter(role='hospital').select_related('user'),
        'claims_list': Claim.objects.select_related('member', 'hospital').all(),
    }
    return render(request, 'dashboard/admin_dashboard.html', context)


# -------------------
# Agent Dashboard
# -------------------
@login_required
def agent_dashboard(request):
    """Agents see only members they registered and their claims."""
    if request.user.profile.role != "agent":
        messages.error(request, "Access denied.")
        return redirect('claim_dashboard')

    members = Member.objects.filter(registered_by=request.user)
    total_members = members.count()
    # Claims submitted by their members
    claims = Claim.objects.filter(member__in=members)
    total_claims = claims.count()
    total_pending = claims.filter(status="Pending").count()
    total_approved = claims.filter(status="Approved").count()
    total_rejected = claims.filter(status="Rejected").count()
    total_forwarded = claims.filter(status="Forwarded").count()
    total_amount = claims.aggregate(Sum('amount'))['amount__sum'] or 0

    context = {
        'members': members,
        'total_members': total_members,
        'claims': claims,
        'total_claims': total_claims,
        'total_pending': total_pending,
        'total_approved': total_approved,
        'total_rejected': total_rejected,
        'total_forwarded': total_forwarded,
        'total_amount': total_amount,
    }
    return render(request, 'dashboard/agent_dashboard.html', context)


# -------------------
# Claim Officer Dashboard
# -------------------
@login_required
def claim_dashboard(request):
    user = request.user
    role = user.profile.role

    if role == "admin":
        claims = Claim.objects.all()
    elif role == "claim_officer":
        # Only claims assigned to this officer
        claims = Claim.objects.filter(assigned_officer=user)
    elif role == "hospital":
        claims = Claim.objects.filter(hospital=user)
    else:  # regular member
        member = getattr(user, 'member_profile', None)
        claims = Claim.objects.filter(member=member) if member else Claim.objects.none()

    # Totals
    total_claims = claims.count()
    total_pending = claims.filter(status="Pending").count()
    total_approved = claims.filter(status="Approved").count()
    total_rejected = claims.filter(status="Rejected").count()
    total_forwarded = claims.filter(status="Forwarded").count()
    total_amount = claims.aggregate(Sum('amount'))['amount__sum'] or 0

    context = {
        "claims": claims,
        "total_claims": total_claims,
        "total_pending": total_pending,
        "total_approved": total_approved,
        "total_rejected": total_rejected,
        "total_forwarded": total_forwarded,
        "total_amount": total_amount,
        "role": role,
    }
    return render(request, "dashboard/claim_dashboard.html", context)


# -------------------
# Hospital Dashboard
# -------------------
@login_required
def hospital_dashboard(request):
    user = request.user
    if user.profile.role != "hospital":
        messages.error(request, "Access denied.")
        return redirect("claim_dashboard")

    # Claims submitted to this hospital
    claims = Claim.objects.filter(hospital=user)

    total_claims = claims.count()
    total_pending = claims.filter(status="Pending").count()
    total_approved = claims.filter(status="Approved").count()
    total_rejected = claims.filter(status="Rejected").count()
    total_forwarded = claims.filter(status="Forwarded").count()
    total_amount = claims.aggregate(Sum('amount'))['amount__sum'] or 0

    context = {
        "claims": claims,
        "total_claims": total_claims,
        "total_pending": total_pending,
        "total_approved": total_approved,
        "total_rejected": total_rejected,
        "total_forwarded": total_forwarded,
        "total_amount": total_amount,
        "non_editable_status": ["Approved", "Rejected"],
    }
    return render(request, "dashboard/hospital_dashboard.html", context)


# -------------------
# Customer Dashboard
# -------------------
@login_required
def customer_dashboard(request):
    user = request.user
    member = getattr(user, 'member_profile', None)
    if not member:
        messages.error(request, "Access denied.")
        return redirect('claim_dashboard')

    claims = Claim.objects.filter(member=member)
    policies = Policy.objects.filter(members=member)

    context = {
        'member': member,
        'claims': claims,
        'policies': policies,
    }
    return render(request, 'dashboard/customer_dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def user_list(request):
    """List all system users for the admin"""
    users = Profile.objects.select_related('user').all().order_by('-user__date_joined')

    # Format users for the template
    for u in users:
        u.name = u.user.get_full_name() or u.user.username
        u.email = u.user.email
        u.role_display = u.get_role_display()
        u.status = "Active" if u.user.is_active else "Inactive"

    return render(request, 'dashboard/users.html', {'users': users})



from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView
from .models import Claim
from .forms import ClaimForm

# ==========================
#      CLAIM LIST VIEW
# ==========================
class ClaimListView(ListView):
    model = Claim
    template_name = "claim/claim_list.html"
    context_object_name = "claims"

    def get_queryset(self):
        user = self.request.user
        role = user.profile.role

        if role == "admin":
            return Claim.objects.filter(status__in=["Pending", "Approved", "Forwarded"])
        elif role == "claim_officer":
            return Claim.objects.filter(status__in=["Pending", "Forwarded"])
        elif role == "hospital":
            return Claim.objects.filter(hospital=user)
        else:
            return Claim.objects.filter(member__user=user)


# ==========================
#      CLAIM DETAIL VIEW
# ==========================
class ClaimDetailView(DetailView):
    model = Claim
    template_name = "claim/claim_detail.html"
    context_object_name = "claim"


# ==========================
#      HOSPITAL CREATE/EDIT CLAIM

# ==========================

@login_required
def hospital_add_claim(request):
    """Allow hospitals to create a new claim"""
    user = request.user

    if user.profile.role != "hospital":
        messages.error(request, "Only hospitals can add claims.")
        return redirect("claim_list")

    if request.method == "POST":
        form = ClaimForm(request.POST, request.FILES, user=user)
        if form.is_valid():
            claim = form.save(commit=False)
            claim.hospital = user
            claim.status = "Pending"
            claim.save()
            messages.success(request, "Claim submitted successfully.")
            return redirect("claim_detail", pk=claim.pk)
    else:
        form = ClaimForm(user=user)

    return render(request, "claim/claim_form.html", {"form": form})

@login_required
def hospital_create_edit_claim(request, pk=None):
    user = request.user
    if user.profile.role != "hospital":
        messages.error(request, "Only hospitals can file or edit claims.")
        return redirect("claim_list")

    claim = None
    if pk:
        claim = get_object_or_404(Claim, pk=pk, hospital=user)
        if claim.status in ["Approved", "Rejected"]:
            messages.error(request, "Cannot edit approved or rejected claims.")
            return redirect("claim_detail", pk=pk)

    if request.method == "POST":
        form = ClaimForm(request.POST, instance=claim, user=user)
        if form.is_valid():
            claim = form.save(commit=False)
            claim.hospital = user
            claim.status = "Pending"
            claim.save()
            messages.success(request, "Claim submitted successfully.")
            return redirect("claim_detail", pk=claim.pk)
    else:
        form = ClaimForm(instance=claim, user=user)

    return render(request, "claims/claim_form.html", {"form": form})


# ==========================
#      CLAIM OFFICER ACTIONS
# ==========================
@login_required
def claim_officer_action(request, pk, action):
    claim = get_object_or_404(Claim, pk=pk)
    user_role = request.user.profile.role

    if user_role != "claim_officer":
        messages.error(request, "Only claim officers can perform this action.")
        return redirect("claim_list")

    if action == "approve":
        claim.status = "Approved"
        claim.approved_by = request.user
        claim.save()
        messages.success(request, "Claim approved successfully.")

    elif action == "reject":
        claim.status = "Rejected"
        claim.approved_by = request.user
        claim.save()
        messages.success(request, "Claim rejected.")

    elif action == "forward":
        claim.status = "Forwarded"
        claim.forwarded_by = request.user
        claim.save()
        messages.success(request, "Claim forwarded to admin for review.")

    else:
        messages.error(request, "Invalid action.")

    return redirect("claim_detail", pk=claim.pk)
