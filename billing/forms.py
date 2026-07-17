from decimal import Decimal

from django import forms
from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce
from django.forms import inlineformset_factory
from .models import Invoice, InvoiceItem, Payment, Party, CompanyProfile

# Lets templates show `inv.total_amount - inv.total_received` without each
# invoice in a dropdown re-querying its payments (was N+1 on every invoice
# in the system when rendering the payment form).
_WITH_RECEIVED = Coalesce(Sum('payments__amount'), Decimal('0'), output_field=DecimalField())


class PartyForm(forms.ModelForm):
    class Meta:
        model = Party
        fields = ['name', 'address', 'city', 'state', 'state_code', 'gstin', 'contact_person', 'phone']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }


class CompanyProfileForm(forms.ModelForm):
    class Meta:
        model = CompanyProfile
        fields = '__all__'
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            'invoice_no', 'date', 'party', 'order_number', 'order_date',
            'place_of_supply', 'challan_no', 'challan_date',
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'order_date': forms.DateInput(attrs={'type': 'date'}),
            'challan_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['invoice_no'].required = False
        self.fields['invoice_no'].help_text = 'Leave blank for auto-generated number'
        self.fields['party'].queryset = Party.objects.order_by('name')
        for field in self.fields.values():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'


class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = [
            'hsn_code', 'description', 'make', 'qty', 'unit',
            'rate', 'discount', 'cgst_rate', 'sgst_rate',
        ]
        widgets = {
            'qty': forms.NumberInput(attrs={'step': '0.001', 'class': 'form-control qty-input'}),
            'rate': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control rate-input'}),
            'discount': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control disc-input'}),
            'cgst_rate': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control cgst-rate-input'}),
            'sgst_rate': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control sgst-rate-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                if isinstance(field.widget, forms.Select):
                    field.widget.attrs['class'] = 'form-select'
                else:
                    field.widget.attrs['class'] = 'form-control'


InvoiceItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    form=InvoiceItemForm,
    extra=0,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['party', 'invoice', 'amount', 'date', 'mode', 'reference_no', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        party_id = kwargs.pop('party_id', None)
        super().__init__(*args, **kwargs)
        self.fields['party'].queryset = Party.objects.order_by('name')
        self.fields['invoice'].queryset = Invoice.objects.annotate(total_received=_WITH_RECEIVED).order_by('-date')
        self.fields['invoice'].required = False
        if party_id:
            self.fields['party'].initial = party_id
            self.fields['invoice'].queryset = Invoice.objects.filter(
                party_id=party_id
            ).annotate(total_received=_WITH_RECEIVED).order_by('-date')
        for field in self.fields.values():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'


class DateRangeFilterForm(forms.Form):
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='From',
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='To',
    )
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search...'}),
        label='Search',
    )
    party = forms.ModelChoiceField(
        queryset=Party.objects.order_by('name'),
        required=False,
        empty_label='All Parties',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
