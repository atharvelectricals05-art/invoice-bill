from decimal import Decimal
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class CompanyProfile(models.Model):
    """Singleton model — only one row should ever exist."""
    name = models.CharField(max_length=200)
    formerly_known_as = models.CharField(max_length=200, blank=True)
    address = models.TextField()
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    gstin = models.CharField(max_length=15, blank=True, verbose_name='GSTIN')
    pan = models.CharField(max_length=10, blank=True, verbose_name='PAN')
    bank_name = models.CharField(max_length=100, blank=True)
    bank_branch = models.CharField(max_length=100, blank=True)
    bank_account_no = models.CharField(max_length=30, blank=True, verbose_name='Bank Account No.')
    neft_ifsc = models.CharField(max_length=11, blank=True, verbose_name='NEFT/IFSC Code')
    msme_no = models.CharField(max_length=50, blank=True, verbose_name='MSME No.')
    logo = models.ImageField(upload_to='company/', blank=True, null=True)

    class Meta:
        verbose_name = 'Company Profile'
        verbose_name_plural = 'Company Profile'

    def __str__(self):
        return self.name

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={'name': 'Atharva Electricals', 'address': ''})
        return obj


class Party(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    state_code = models.CharField(max_length=5, blank=True)
    gstin = models.CharField(max_length=15, blank=True, verbose_name='GSTIN')
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name_plural = 'Parties'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_balance(self):
        """Returns dict with total_invoiced, total_received, outstanding."""
        from billing.utils import get_party_balance
        return get_party_balance(self)


def _next_invoice_no():
    """Auto-generate sequential invoice number like ISL-000724."""
    from django.db.models import Max
    last = Invoice.objects.aggregate(max_no=Max('_seq'))['max_no'] or 0
    seq = last + 1
    return seq


class Invoice(models.Model):
    STATUS_UNPAID = 'unpaid'
    STATUS_PARTIAL = 'partial'
    STATUS_PAID = 'paid'
    STATUS_CHOICES = [
        (STATUS_UNPAID, 'Unpaid'),
        (STATUS_PARTIAL, 'Partial'),
        (STATUS_PAID, 'Paid'),
    ]

    invoice_no = models.CharField(max_length=20, unique=True, blank=True)
    _seq = models.PositiveIntegerField(default=0, editable=False)
    date = models.DateField(default=timezone.localdate)
    party = models.ForeignKey(Party, on_delete=models.PROTECT, related_name='invoices')
    order_number = models.CharField(max_length=50, blank=True)
    order_date = models.DateField(null=True, blank=True)
    place_of_supply = models.CharField(max_length=100, blank=True)
    challan_no = models.CharField(max_length=50, blank=True)
    challan_date = models.DateField(null=True, blank=True)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    cgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    sgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    round_off = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-_seq']

    def __str__(self):
        return self.invoice_no

    def save(self, *args, **kwargs):
        if not self.invoice_no:
            # Generate sequential number
            from django.db.models import Max
            last = Invoice.objects.aggregate(max_no=Max('_seq'))['max_no'] or 0
            self._seq = last + 1
            self.invoice_no = f'ISL-{self._seq:06d}'
        super().save(*args, **kwargs)

    def recalculate(self):
        """Recompute totals from InvoiceItems and save."""
        items = self.items.all()
        subtotal = sum(item.taxable_value for item in items) or Decimal('0')
        cgst = sum(item.cgst_amount for item in items) or Decimal('0')
        sgst = sum(item.sgst_amount for item in items) or Decimal('0')
        raw_total = subtotal + cgst + sgst
        rounded = round(raw_total)
        round_off = Decimal(str(rounded)) - raw_total

        self.subtotal = subtotal
        self.cgst_amount = cgst
        self.sgst_amount = sgst
        self.round_off = round_off
        self.total_amount = Decimal(str(rounded))
        self.save(update_fields=['subtotal', 'cgst_amount', 'sgst_amount', 'round_off', 'total_amount'])

    def get_total_received(self):
        return self.payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')

    def get_outstanding(self):
        return self.total_amount - self.get_total_received()

    def get_status(self):
        outstanding = self.get_outstanding()
        if outstanding <= 0:
            return self.STATUS_PAID
        elif self.get_total_received() > 0:
            return self.STATUS_PARTIAL
        return self.STATUS_UNPAID

    def get_status_display_label(self):
        s = self.get_status()
        return dict(self.STATUS_CHOICES).get(s, s)


class InvoiceItem(models.Model):
    UNIT_CHOICES = [
        ('NOS', 'NOS'),
        ('PCS', 'PCS'),
        ('MTR', 'MTR'),
        ('KG', 'KG'),
        ('BOX', 'BOX'),
        ('SET', 'SET'),
        ('RFT', 'RFT'),
        ('PKT', 'PKT'),
        ('OTH', 'Other'),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    hsn_code = models.CharField(max_length=10, blank=True, verbose_name='HSN Code')
    description = models.CharField(max_length=300)
    make = models.CharField(max_length=100, blank=True, help_text='e.g. MAKE - 3M')
    qty = models.DecimalField(max_digits=10, decimal_places=3)
    unit = models.CharField(max_length=5, choices=UNIT_CHOICES, default='NOS')
    rate = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    taxable_value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    cgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('9.00'), verbose_name='CGST Rate %')
    cgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    sgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('9.00'), verbose_name='SGST Rate %')
    sgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.description} ({self.invoice.invoice_no})'

    def save(self, *args, **kwargs):
        # Auto-calculate derived fields
        self.taxable_value = (self.qty * self.rate) - self.discount
        self.cgst_amount = (self.taxable_value * self.cgst_rate / 100).quantize(Decimal('0.01'))
        self.sgst_amount = (self.taxable_value * self.sgst_rate / 100).quantize(Decimal('0.01'))
        self.line_total = self.taxable_value + self.cgst_amount + self.sgst_amount
        super().save(*args, **kwargs)


class Payment(models.Model):
    MODE_CHOICES = [
        ('Cash', 'Cash'),
        ('Cheque', 'Cheque'),
        ('NEFT/RTGS', 'NEFT/RTGS'),
        ('UPI', 'UPI'),
        ('Other', 'Other'),
    ]

    party = models.ForeignKey(Party, on_delete=models.PROTECT, related_name='payments')
    invoice = models.ForeignKey(
        Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.localdate)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='NEFT/RTGS')
    reference_no = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'₹{self.amount} from {self.party.name} on {self.date}'
