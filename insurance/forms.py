from django import forms
from django.contrib.auth.models import User
from .models import Profile, Member
from .models import Claim, Member


# --- Admin creates Agents, Hospitals, Claim Officers ---
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


from django import forms
from django.contrib.auth.models import User
from .models import Member


# --- Member Registration Form (used by agents) ---
class MemberRegistrationForm(forms.ModelForm):
    # Fields for new user (customer)
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Member
        fields = ['policy', 'phone', 'address', 'date_of_birth']
        widgets = {
            'policy': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def clean_password2(self):
        p1 = self.cleaned_data.get('password')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match")
        return p2




class ClaimForm(forms.ModelForm):
    class Meta:
        model = Claim
        fields = ['member', 'amount', 'date_of_service', 'notes']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # We can pass current user to filter members
        super().__init__(*args, **kwargs)

        if user:
            role = user.profile.role

            if role == 'hospital':
                # Hospital can only file claims for members assigned to them
                # Here we assume all members can be selected; optionally filter if needed
                self.fields['member'].queryset = Member.objects.all()
            elif role == 'claim_officer':
                # Claim officer can edit all claims
                self.fields['member'].queryset = Member.objects.all()
            else:
                # Other users cannot change member
                self.fields['member'].widget = forms.HiddenInput()
