from django import forms


class ShippingForm(forms.Form):
    shipping_method = forms.ChoiceField(
        choices=[
            ('standard',  'Standard'),
            ('express',   'Express'),
            ('overnight', 'Overnight'),
        ],
        widget=forms.RadioSelect,
        initial='standard',
    )


class CouponForm(forms.Form):
    coupon_code = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Enter coupon code'}),
    )

    def clean_coupon_code(self):
        return self.cleaned_data.get('coupon_code', '').strip().upper()