from django import forms
from .models import Review


class ReviewForm(forms.ModelForm):
    rating = forms.IntegerField(
        min_value=1, max_value=5,
        widget=forms.HiddenInput(),
        error_messages={'required': 'Please select a star rating.'}
    )

    class Meta:
        model   = Review
        fields  = ['rating', 'title', 'body']
        widgets = {
            'title': forms.TextInput(attrs={
                'class':       'form-control',
                'placeholder': 'Summarise your experience',
                'maxlength':   200,
            }),
            'body': forms.Textarea(attrs={
                'class':       'form-control',
                'rows':        4,
                'placeholder': 'Tell others what you thought of this product…',
            }),
        }

    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if not rating or not (1 <= rating <= 5):
            raise forms.ValidationError('Please select a star rating.')
        return rating