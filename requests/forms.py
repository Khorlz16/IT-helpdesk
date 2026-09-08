from django import forms
from .models import Request, RequestItem

class RequestForm(forms.ModelForm):
    class Meta:
        model = Request
        fields = ['category', 'description', 'requested_priority']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select modern-field'}),
            'description': forms.Textarea(attrs={'rows': 5, 'class': 'form-control modern-field', 'placeholder': 'Tell us what the issue is and any important details…'}),
            'requested_priority': forms.Select(attrs={'class': 'form-select modern-field'}),
        }

class RequestItemForm(forms.ModelForm):
    class Meta:
        model = RequestItem
        fields = ['item_name', 'quantity']
        widgets = {
            'item_name': forms.TextInput(attrs={'class': 'form-control modern-field', 'placeholder': 'Item name'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control modern-field', 'min': '1', 'placeholder': 'Qty'}),
        }
