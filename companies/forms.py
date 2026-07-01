from django import forms


class SearchForm(forms.Form):
    q = forms.CharField(
        label='جستجو',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'نام یا نماد شرکت را وارد کنید...',
            'autocomplete': 'off',
        }),
    )