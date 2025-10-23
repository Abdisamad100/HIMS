from django import forms
from django.contrib.auth.models import User
from .models import Profile, Member, Policy, Claim, MemberPolicy
from django.utils.translation import gettext_lazy as _


# ====================================================
# ADMIN USER CREATION (Agents, Hospitals, Claim Officers)
# ====================================================
class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def clean_password2(self):
        p1 = self.cleaned_data.get('password')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        return p2


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['role']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
        }


# ====================================================
# MEMBER REGISTRATION (used by agents)
# ====================================================
class MemberRegistrationForm(forms.ModelForm):
    # --- Fields for creating new User (Customer) ---
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    # --- Select a policy at registration time (optional) ---
    policy = forms.ModelChoiceField(
        queryset=Policy.objects.filter(status='active'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_("Assign Policy"),
    )

    class Meta:
        model = Member
        fields = ['phone', 'address', 'date_of_birth', 'policy']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def clean_password2(self):
        p1 = self.cleaned_data.get('password')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        return p2
    def clean_username(self):
         username = self.cleaned_data.get('username')
         if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken. Please choose another.")
            return username

    def save(self, registered_by=None, commit=True):
        """Create User + Member + optional MemberPolicy."""
        cleaned = self.cleaned_data
        username = cleaned['username']
        password = cleaned['password']

        # --- Create the user account ---
        user = User.objects.create_user(
            username=username,
            first_name=cleaned['first_name'],
            last_name=cleaned['last_name'],
            email=cleaned['email'],
            password=password,
        )

        # --- Assign the profile role automatically ---
        user.profile.role = 'customer'
        user.profile.save()

        # --- Create the Member instance ---
        member = Member.objects.create(
            user=user,
            phone=cleaned['phone'],
            address=cleaned['address'],
            date_of_birth=cleaned.get('date_of_birth'),
            registered_by=registered_by,
        )

        # --- Optionally assign a policy to this member ---
        policy = cleaned.get('policy')
        if policy:
            MemberPolicy.objects.create(member=member, policy=policy)

        return member


# ====================================================
# CLAIM FORM
# ====================================================
class ClaimForm(forms.ModelForm):
    class Meta:
        model = Claim
        fields = ['member_policy', 'amount', 'date_of_service', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter claim amount'}),
            'date_of_service': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter claim notes or description'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Customize queryset based on user role
        if user:
            role = getattr(user.profile, 'role', None)

            if role == 'hospital':
                self.fields['member_policy'].queryset = MemberPolicy.objects.select_related(
                    'member__user', 'policy'
                ).filter(policy__status='active')

            elif role == 'claim_officer':
                self.fields['member_policy'].queryset = MemberPolicy.objects.select_related(
                    'member__user', 'policy'
                )
            else:
                self.fields['member_policy'].widget = forms.HiddenInput()

        # Custom readable label
        self.fields['member_policy'].label_from_instance = (
            lambda obj: f"{obj.member.user.get_full_name()} — {obj.policy.policy_number} ({obj.policy.name})"
        )


# ====================================================
# POLICY CREATION FORM
# ====================================================
class PolicyForm(forms.ModelForm):
    class Meta:
        model = Policy
        fields = ['policy_number', 'name', 'description', 'premium', 'start_date', 'end_date', 'status']
        widgets = {
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'premium': forms.NumberInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'policy_number': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
