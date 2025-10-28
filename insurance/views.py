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
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Profile, Member, Policy, Claim
from django.http import JsonResponse
from django.db.models import Q
import random, string
from django.db import transaction
from django.db.models import Sum,Count

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Profile, MemberPolicy
from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import MemberPolicy



from .forms import (
    UserRegistrationForm,
    ProfileForm,
    MemberRegistrationForm,
    PolicyForm,
)
from .models import Profile, Member


# ============================================================
# 🔐 ROLE-BASED DASHBOARD REDIRECTOR
# ============================================================

def is_admin(user):
    return hasattr(user, 'profile') and user.profile.role == 'admin'


def is_agent(user):
    return hasattr(user, 'profile') and user.profile.role == 'agent'

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



# ============================================================
# 🏛️ ADMIN VIEWS
# ============================================================
@login_required
def admin_dashboard(request):
    # --- Access Control ---
    if request.user.profile.role != "admin":
        messages.error(request, "Access denied.")
        return redirect('claim_dashboard')

    # --- General Counts ---
    users_count = Profile.objects.count()
    admin_count = Profile.objects.filter(role='admin').count()
    agents_count = Profile.objects.filter(role='agent').count()
    hospitals_count = Profile.objects.filter(role='hospital').count()
    claim_officers_count = Profile.objects.filter(role='claim_officer').count()
    customers_count = Profile.objects.filter(role='customer').count()

    # --- Claim Stats ---
    claims_count = Claim.objects.count()
    claims_pending = Claim.objects.filter(status='Pending').count()
    claims_approved = Claim.objects.filter(status='Approved').count()
    claims_rejected = Claim.objects.filter(status='Rejected').count()
    claims_reimbursed = Claim.objects.filter(status='Reimbursed').count()

    # Build stats dictionary for easy display
    stats = {
        'Pending': claims_pending,
        'Approved': claims_approved,
        'Rejected': claims_rejected,
        'Reimbursed': claims_reimbursed,
    }

    # --- Policy Stats ---
    policies = Policy.objects.all().order_by('-created_at')
    total_policies = policies.count()
    active_policies = policies.filter(status='active').count()
    expired_policies = policies.filter(status='expired').count()
    total_premium = policies.aggregate(total=Sum('premium'))['total'] or 0

    # --- Recent Activity ---
    recent_users = Profile.objects.select_related('user').order_by('-user__date_joined')[:5]
    recent_claims = Claim.objects.select_related('member_policy__member__user', 'hospital').order_by('-created_at')[:5]

    # --- Hospitals ---
    hospital_list = (
    Profile.objects
    .filter(role='hospital')
    .select_related('user')
    .order_by('user__username')
)

    # --- Context ---
    context = {
        # Counts
        'users_count': users_count,
        'admin_count': admin_count,
        'agents_count': agents_count,
        'hospitals_count': hospitals_count,
        'claim_officers_count': claim_officers_count,
        'customers_count': customers_count,
        'claims_count': claims_count,

        # Policy
        'policies': policies,
        'total_policies': total_policies,
        'active_policies': active_policies,
        'expired_policies': expired_policies,
        'total_premium': total_premium,

        # Claim stats
        'stats': stats,
        'claims_list': Claim.objects.all(),
        'recent_claims': recent_claims,
        'recent_users': recent_users,
        'role': request.user.profile.role,
        'hospital_list': hospital_list,
    }

    return render(request, 'dashboard/admin_dashboard.html', context)

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




@login_required
def filter_users(request):
    # Restrict access to admin only
    if request.user.profile.role.lower() != "admin":
        return JsonResponse({'error': 'Access denied'}, status=403)

    role = request.GET.get('role', 'all')
    search = request.GET.get('search', '').strip().lower()

    users = Profile.objects.select_related('user')

    # Role filter
    if role != 'all':
        users = users.filter(role__iexact=role)

    # Search filter
    if search:
        users = users.filter(
            Q(user__username__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__email__icontains=search) |
            Q(role__icontains=search)
        )

    user_data = [
        {
            'id': u.id,
            'name': u.user.get_full_name() or u.user.username,
            'email': u.user.email,
            'role': u.role.title(),
            'joined': u.user.date_joined.strftime('%Y-%m-%d'),
        }
        for u in users
    ]

    return JsonResponse({'users': user_data})


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





@login_required
def edit_user(request, pk):
    """Admin edits user details (name, email, phone)."""
    if request.user.profile.role != 'admin':
        messages.error(request, "Access denied.")
        return redirect('claim_dashboard')

    profile = get_object_or_404(Profile, pk=pk)
    user = profile.user

    if request.method == 'POST':
        full_name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')

        # Split full name
        if full_name:
            parts = full_name.split(' ', 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ''
        user.email = email
        user.save()

        profile.phone_number = phone
        profile.save()

        messages.success(request, f"{user.username} updated successfully.")
        return redirect('admin_dashboard')

    context = {'profile': profile}
    return render(request, 'user/edit_user.html', context)


@login_required
def toggle_user_status(request, pk):
    """Admin can suspend or activate any user."""
    if request.user.profile.role != 'admin':
        messages.error(request, "Access denied.")
        return redirect('claim_dashboard')

    profile = get_object_or_404(Profile, pk=pk)
    user = profile.user

    user.is_active = not user.is_active
    user.save()

    state = "activated" if user.is_active else "suspended"
    messages.success(request, f"{user.username} has been {state}.")
    return redirect('admin_dashboard')



# ============================================================
# 🧾 AGENT VIEWS
# ============================================================

# -------------------
# Agent Dashboard
# -------------------
@login_required
def agent_dashboard(request):
    if request.user.profile.role != "agent":
        messages.error(request, "Access denied.")
        return redirect('claim_dashboard')

    members = Member.objects.filter(registered_by=request.user).prefetch_related('policies__payments', 'policies__policy')

    # Prepare member_data for template
    member_data = []
    for member in members:
        policies_info = []
        for mp in member.policies.all():
            total_paid = sum(p.amount for p in mp.payments.all())
            policies_info.append({
                'member_policy': mp,
                'policy_name': mp.policy.name,
                'policy_number': mp.member_policy_number,
                'premium': mp.policy.premium,
                'total_paid': total_paid,
                'remaining': mp.policy.premium - total_paid,
            })
        member_data.append({
            'member': member,
            'policies': policies_info
        })

    context = {
        'member_data': member_data
    }
    return render(request, 'dashboard/agent_dashboard.html', context)


@login_required
def edit_agent(request, pk):
    """Admin edits an agent's details."""
    if request.user.profile.role != "admin":
        messages.error(request, "Access denied.")
        return redirect('claim_dashboard')

    profile = get_object_or_404(Profile, pk=pk, role='agent')

    if request.method == 'POST':
        full_name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')

        user = profile.user
        if full_name:
            parts = full_name.split(' ', 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ''
        user.email = email
        user.save()

        profile.phone_number = phone
        profile.save()

        messages.success(request, "Agent updated successfully.")
        return redirect('admin_dashboard')

    context = {'profile': profile}
    return render(request, 'agent/edit_agent.html', context)


@login_required
def toggle_agent_status(request, pk):
    """Admin can suspend/activate an agent."""
    if request.user.profile.role != "admin":
        messages.error(request, "Access denied.")
        return redirect('claim_dashboard')

    profile = get_object_or_404(Profile, pk=pk, role='agent')
    profile.user.is_active = not profile.user.is_active
    profile.user.save()

    status = "activated" if profile.user.is_active else "suspended"
    messages.success(request, f"Agent {status} successfully.")
    return redirect('admin_dashboard')


# ==========================
#     MEMBER REGISTRATION
# ==========================


@user_passes_test(is_agent)
@login_required
def register_member(request):
    """Agents register new members and optionally assign them a policy."""
    if request.user.profile.role not in ["agent", "admin"]:
        messages.error(request, "Only agents or admins can register members.")
        return redirect("dashboard")

    if request.method == "POST":
        form = MemberRegistrationForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    # --- USER CREATION ---
                    first_name = form.cleaned_data["first_name"]
                    last_name = form.cleaned_data["last_name"]
                    email = form.cleaned_data["email"]
                    password = form.cleaned_data["password"]
                    username = form.cleaned_data.get("username")

                    # ✅ Auto-generate username if empty
                    if not username or username.strip() == "":
                        base_username = (first_name + last_name).lower().replace(" ", "")
                        username = base_username
                        counter = 1
                        while User.objects.filter(username=username).exists():
                            username = f"{base_username}{counter}"
                            counter += 1

                    # ✅ Create new user (customer)
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        first_name=first_name,
                        last_name=last_name,
                        password=password,
                    )
                    user.profile.role = "customer"
                    user.profile.save()

                    # --- MEMBER CREATION ---
                    member = Member.objects.create(
                        user=user,
                        phone=form.cleaned_data["phone"],
                        address=form.cleaned_data["address"],
                        date_of_birth=form.cleaned_data["date_of_birth"],
                        registered_by=request.user,
                    )

                    # --- OPTIONAL POLICY ASSIGNMENT ---
                    selected_policy = form.cleaned_data.get("policy")
                    if selected_policy:
                        MemberPolicy.objects.create(
                            member=member,
                            policy=selected_policy,
                        )

                    messages.success(
                        request,
                        f"✅ Member {user.get_full_name()} registered successfully.",
                    )
                    return redirect("member_list")

            except Exception as e:
                messages.error(request, f"❌ Error during registration: {e}")

        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = MemberRegistrationForm()

    return render(request, "registration/register_member.html", {"form": form})



@login_required
def verify_member_policy(request):
    if request.user.profile.role.lower() != "hospital":
        messages.error(request, "Only hospitals can verify members for claims.")
        return redirect("claim_list")

    member = None
    policies = None

    if request.method == "POST":
        search = request.POST.get("search", "").strip()
        if not search:
            messages.warning(request, "Please enter a phone, email, or member policy number.")
            return redirect("verify_member_policy")

        member_policy = (
            MemberPolicy.objects.select_related("member__user", "policy")
            .filter(
                Q(member__phone__iexact=search)
                | Q(member__user__email__iexact=search)
                | Q(member_policy_number__iexact=search),
                is_active=True,
                policy__status="active",
            )
            .first()
        )

        if member_policy:
            member = member_policy.member
            policies = [member_policy.policy]

            request.session["verified_member_policy_id"] = member_policy.id
            request.session.modified = True

            messages.success(
                request,
                f"✅ Verified member: {member.user.get_full_name()} — "
                f"Policy {member_policy.member_policy_number} ({member_policy.policy.name})",
            )
            return redirect("hospital_book_service")
        else:
            messages.error(
                request,
                "❌ No active member or policy found for that phone, email, or member policy number.",
            )

    return render(request, "claim/verify_member_policy.html", {"member": member, "policies": policies})


@login_required
def hospital_book_service(request):
    """
    Step 2: Hospital records service details (treatment info)
    for a verified member-policy before filing the claim.
    """
    # Restrict to hospitals
    if request.user.profile.role.lower() != "hospital":
        messages.error(request, "Only hospitals can record services.")
        return redirect("claim_list")

    member_policy_id = request.session.get("verified_member_policy_id")

    if not member_policy_id:
        messages.warning(request, "Please verify a member first.")
        return redirect("verify_member_policy")

    member_policy = get_object_or_404(MemberPolicy, id=member_policy_id)

    if request.method == "POST":
        notes = request.POST.get("notes", "").strip()
        amount = request.POST.get("amount", "").strip()
        date_of_service = request.POST.get("date_of_service", "").strip()

        if not (amount and date_of_service):
            messages.warning(request, "Amount and Date of Service are required.")
            return redirect("hospital_book_service")

        # Save treatment info temporarily in session
        request.session["treatment_info"] = {
            "notes": notes,
            "amount": amount,
            "date_of_service": date_of_service,
        }
        request.session.modified = True

        messages.success(request, "✅ Service recorded successfully. Proceed to file claim.")
        return redirect("hospital_add_claim")

    context = {
        "member_policy": member_policy,
        "member": member_policy.member,
        "policy": member_policy.policy,
    }

    return render(request, "claim/hospital_book_service.html", context)


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


@login_required
def profile_view(request):
    return render(request, 'dashboard/profile.html', {'user': request.user})

# ============================================================
# 🧾 POLICY VIEWS
# ============================================================


# --- List all policies ---
@login_required
def policy_list(request):
    policies = Policy.objects.all().order_by('-created_at')
    return render(request, 'policy/policy_list.html', {'policies': policies})


# --- Create new policy ---
@login_required
def create_policy(request):
    if request.method == 'POST':
        form = PolicyForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Policy created successfully.")
            return redirect('policy_list')
    else:
        form = PolicyForm()
    return render(request, 'policy/create_policy.html', {'form': form})




# ==========================
#        EDIT POLICY
# ==========================
def edit_policy(request, policy_id):
    if request.user.profile.role != 'admin':
        messages.error(request, "Access denied.")
        return redirect('admin_dashboard')

    policy = get_object_or_404(Policy, id=policy_id)
    if request.method == 'POST':
        form = PolicyForm(request.POST, instance=policy)
        if form.is_valid():
            form.save()
            messages.success(request, "Policy updated successfully.")
            return redirect('admin_dashboard')
    else:
        form = PolicyForm(instance=policy)

    return render(request, 'policy/edit_policy.html', {'form': form, 'policy': policy})


# ==========================
#        DELETE POLICY
# ==========================
def delete_policy(request, policy_id):
    if request.user.profile.role != 'admin':
        messages.error(request, "Access denied.")
        return redirect('admin_dashboard')

    policy = get_object_or_404(Policy, id=policy_id)

    if request.method == 'POST':
        policy.delete()
        messages.success(request, "Policy deleted successfully.")
        return redirect('admin_dashboard')

    return render(request, 'policy/delete_policy.html', {'policy': policy})






# ============================================================
# 🧾 CLAIM VIEWS
# ============================================================

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
        claims = Claim.objects.filter(status__in=["Pending", "Forwarded"])
    elif role == "hospital":
        claims = Claim.objects.filter(hospital=user)
    else:  # member
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
        elif role == "customer":
            return Claim.objects.filter(member_policy__member__user=user)
        else:
            return Claim.objects.none()

# ==========================
#      CLAIM DETAIL VIEW
# ==========================
class ClaimDetailView(DetailView):
    model = Claim
    template_name = "claim/claim_detail.html"
    context_object_name = "claim"

# ==========================
#   HOSPITAL CREATE / EDIT CLAIM
# ==========================
@login_required
@login_required
def hospital_add_claim(request):
    """Step 3: Submit Claim after verification and service record"""
    user = request.user

    if user.profile.role != "hospital":
        messages.error(request, "Only hospitals can add claims.")
        return redirect("claim_list")

    member_policy_id = request.session.get("verified_member_policy_id")
    treatment_info = request.session.get("treatment_info")

    if not member_policy_id:
        messages.warning(request, "Please verify member first.")
        return redirect("verify_member_policy")

    member_policy = get_object_or_404(MemberPolicy, id=member_policy_id)

    if request.method == "POST":
        form = ClaimForm(request.POST, request.FILES, user=user)
        if form.is_valid():
            claim = form.save(commit=False)
            claim.hospital = user
            claim.member_policy = member_policy
            claim.status = "Pending"
            claim.save()

            # Clear session
            request.session.pop("verified_member_policy_id", None)
            request.session.pop("treatment_info", None)

            messages.success(request, "✅ Claim submitted successfully.")
            return redirect("claim_detail", pk=claim.pk)
    else:
        initial = treatment_info or {}
        form = ClaimForm(user=user, initial=initial)

    return render(request, "claim/claim_form.html", {
        "form": form,
        "member_policy": member_policy
    })

@login_required
def hospital_create_edit_claim(request, pk=None):
    """Edit or create claim for hospitals."""
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
        form = ClaimForm(request.POST, request.FILES, instance=claim, user=user)
        if form.is_valid():
            claim = form.save(commit=False)
            claim.hospital = user
            claim.status = "Pending"
            claim.save()
            messages.success(request, "Claim submitted successfully.")
            return redirect("claim_detail", pk=claim.pk)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ClaimForm(instance=claim, user=user)

    return render(request, "claim/claim_form.html", {"form": form})

# ==========================
#      CLAIM OFFICER ACTIONS
# ==========================
@login_required
def claim_officer_action(request, pk, action):
    claim = get_object_or_404(Claim, pk=pk)
    role = request.user.profile.role

    # Only officer or admin can act
    if role not in ["claim_officer", "admin"]:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "error": "Permission denied"}, status=403)
        messages.error(request, "Permission denied.")
        return redirect("claim_dashboard")

    # ----- CLAIM OFFICER ACTIONS -----
    if role == "claim_officer":
        if claim.status not in ["Pending", "Forwarded"]:
            return JsonResponse({"success": False, "error": "Cannot modify approved/rejected claims."}, status=400)
        if action == "approve":
            claim.status = "Approved"
            claim.approved_by = request.user
            msg = "Claim approved successfully."
        elif action == "reject":
            claim.status = "Rejected"
            claim.approved_by = request.user
            msg = "Claim rejected."
        elif action == "forward":
            claim.status = "Forwarded"
            claim.forwarded_by = request.user
            msg = "Claim forwarded to admin."
        else:
            msg = "Invalid action."
            return JsonResponse({"success": False, "error": msg}, status=400)

    # ----- ADMIN ACTIONS -----
    elif role == "admin":
        if action == "approve":
            claim.status = "Approved"
            claim.approved_by = request.user
            msg = "Claim approved by admin."
        elif action == "reject":
            claim.status = "Rejected"
            claim.approved_by = request.user
            msg = "Claim rejected by admin."
        elif action == "reimburse":
            claim.status = "Reimbursed"
            claim.reimbursed_by = request.user
            msg = "Reimbursement completed."
        else:
            msg = "Invalid admin action."
            return JsonResponse({"success": False, "error": msg}, status=400)

    claim.save()

    # AJAX response
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"success": True, "message": msg, "status": claim.status})

    messages.success(request, msg)
    return redirect("claim_dashboard")







# ============================================================
# 🧾 HOSPITAL VIEWS
# ============================================================


# -------------------
# Hospital Dashboard
# -------------------
@login_required
def hospital_dashboard(request):
    """Dashboard for hospital users to manage and submit claims."""
    user = request.user

    # ✅ Only hospital users can access this view
    if user.profile.role != "hospital":
        messages.error(request, "Access denied. Only hospitals can submit claims.")
        return redirect("/")

    # =====================================
    #          HANDLE CLAIM SUBMISSION
    # =====================================
    if request.method == "POST":
        policy_number = request.POST.get("policy_number")
        patient_name = request.POST.get("patient_name")
        claim_type = request.POST.get("claim_type")
        amount = request.POST.get("amount")
        documents = request.FILES.getlist("documents")

        try:
            # ✅ Find the related MemberPolicy safely
            member_policy = MemberPolicy.objects.select_related("member", "policy").filter(
                policy__policy_number__iexact=policy_number
            ).first()

            if not member_policy:
                messages.error(request, f"No active policy found for number {policy_number}.")
                return redirect("hospital_dashboard")

            # ✅ Create the claim
            claim = Claim.objects.create(
                member_policy=member_policy,
                hospital=user,
                amount=amount,
                notes=f"Quick claim — {claim_type}",
                status="Pending",
            )

            # ✅ Handle document uploads
            for doc in documents:
                ClaimDocument.objects.create(claim=claim, document=doc)

            messages.success(request, f"Claim #{claim.id} submitted successfully!")
            return redirect("hospital_dashboard")

        except Exception as e:
            messages.error(request, f"Error submitting claim: {e}")
            return redirect("hospital_dashboard")

    # =====================================
    #          DASHBOARD DATA
    # =====================================
    claims = Claim.objects.filter(hospital=user).select_related(
        "member_policy__member__user", "member_policy__policy"
    )

    total_claims = claims.count()
    total_amount = claims.aggregate(total=models.Sum("amount"))["total"] or 0
    pending_claims = claims.filter(status="Pending").count()
    approved_claims = claims.filter(status="Approved").count()
    rejected_claims = claims.filter(status="Rejected").count()

    context = {
        "claims": claims,
        "total_claims": total_claims,
        "total_amount": total_amount,
        "pending_claims": pending_claims,
        "approved_claims": approved_claims,
        "rejected_claims": rejected_claims,
    }

    return render(request, "dashboard/hospital_dashboard.html", context)


@login_required
def hospital_list(request):
    """List all hospitals (admin view) with search support."""
    if request.user.profile.role != 'admin':
        messages.error(request, "Access denied.")
        return redirect('claim_dashboard')

    search_query = request.GET.get('q', '')
    hospitals = Profile.objects.filter(role='hospital')

    if search_query:
        hospitals = hospitals.filter(user__first_name__icontains=search_query) | hospitals.filter(
            user__last_name__icontains=search_query
        ) | hospitals.filter(user__email__icontains=search_query)

    context = {'hospital_list': hospitals, 'search_query': search_query}
    return render(request, 'dashboard/hospitals.html', context)


@login_required
def toggle_hospital_status(request, pk):
    """Activate or suspend a hospital."""
    if request.user.profile.role != 'admin':
        messages.error(request, "Access denied.")
        return redirect('claim_dashboard')

    hospital = get_object_or_404(Profile, pk=pk, role='hospital')
    user = hospital.user
    user.is_active = not user.is_active
    user.save()

    state = "activated" if user.is_active else "suspended"
    messages.success(request, f"{user.get_full_name()} has been {state}.")
    return redirect('hospital_list')

@login_required
def edit_hospital(request, pk):
    hospital = get_object_or_404(Profile, pk=pk, role='hospital')
    user = hospital.user

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        address = request.POST.get('address')

        user.first_name = name
        user.email = email
        user.save()

        hospital.address = address
        hospital.save()

        messages.success(request, f"{user.username} updated successfully.")
        return redirect('admin_dashboard')

    return render(request, 'hospital/edit_hospital.html', {'hospital': hospital})


@login_required
def toggle_hospital_status(request, pk):
    hospital = get_object_or_404(Profile, pk=pk, role='hospital')
    user = hospital.user
    user.is_active = not user.is_active
    user.save()

    state = "activated" if user.is_active else "suspended"
    messages.success(request, f"Hospital '{user.get_full_name()}' has been {state}.")
    return redirect('admin_dashboard')



# ============================================================
# 🧾 CUSTOMER VIEWS
# ============================================================


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


# ============================================================
# 🧾 REPORTS VIEWS
# ============================================================

import csv
from django.http import HttpResponse
from django.contrib.auth.models import User
from .models import Claim  # adjust import to your app

def export_users_csv(request):
    # Set up the HTTP response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Username', 'Full Name', 'Email', 'Is Active', 'Date Joined'])

    for user in User.objects.all():
        writer.writerow([
            user.id,
            user.username,
            user.get_full_name(),
            user.email,
            'Active' if user.is_active else 'Inactive',
            user.date_joined.strftime("%Y-%m-%d"),
        ])

    return response


def export_claims_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="claims_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Policy Number', 'Claimant', 'Status', 'Amount', 'Date Created'])

    for claim in Claim.objects.all():
        writer.writerow([
            claim.id,
            getattr(claim.policy, 'policy_number', 'N/A'),
            getattr(claim.user, 'get_full_name', lambda: 'N/A')(),
            claim.status,
            claim.amount,
            claim.created_at.strftime("%Y-%m-%d"),
        ])

    return response


# ============================================================
# 🧾 PAYMENTS VIEWS
# ============================================================
@login_required
def add_member_payment(request, member_policy_id):
    """
    Record a payment for a member's policy
    """
    member_policy = get_object_or_404(MemberPolicy, id=member_policy_id)

    if request.user.profile.role != 'agent':
        messages.error(request, "Access denied.")
        return redirect('agent_dashboard')

    if request.method == "POST":
        amount = request.POST.get('amount')
        if amount:
            try:
                amount = float(amount)
                payment = MemberPayment.objects.create(
                    member_policy=member_policy,
                    amount=amount,
                    recorded_by=request.user
                )
                messages.success(request, f"Payment of {amount} added successfully.")
            except Exception as e:
                messages.error(request, f"Error recording payment: {str(e)}")
        else:
            messages.error(request, "Please enter a valid amount.")
        return redirect('agent_dashboard')

    return render(request, 'members/add_member_payment.html', {'member_policy': member_policy})