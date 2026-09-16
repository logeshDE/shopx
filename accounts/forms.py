from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Profile, Address


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=50)
    last_name  = forms.CharField(max_length=50)
    email      = forms.EmailField()
    password1  = forms.CharField(widget=forms.PasswordInput)
    password2  = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model  = User
        fields = ['first_name', 'last_name', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']  # email doubles as username
        user.is_email_verified = False
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email    = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)


class ProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50)
    last_name  = forms.CharField(max_length=50)
    phone      = forms.CharField(max_length=15, required=False)

    class Meta:
        model  = Profile
        fields = ['avatar', 'bio', 'date_of_birth', 'gender']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'bio': forms.Textarea(attrs={'rows': 3}),
        }


class AddressForm(forms.ModelForm):
    class Meta:
        model  = Address
        fields = [
            'full_name', 'phone', 'address_line1', 'address_line2',
            'city', 'state', 'pincode', 'country', 'address_type', 'is_default',
        ]
        widgets = {
            'address_type': forms.Select(attrs={'class': 'form-select'}),
            'is_default':   forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }