from django.contrib import admin
from .models import CompanyProfile, Party, Invoice, InvoiceItem, Payment


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'gstin', 'pan', 'phone', 'email')


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    fields = ('description', 'hsn_code', 'make', 'qty', 'unit', 'rate', 'discount',
              'cgst_rate', 'sgst_rate', 'taxable_value', 'cgst_amount', 'sgst_amount', 'line_total')
    readonly_fields = ('taxable_value', 'cgst_amount', 'sgst_amount', 'line_total')


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_no', 'date', 'party', 'total_amount', 'created_at')
    list_filter = ('date', 'party')
    search_fields = ('invoice_no', 'party__name')
    inlines = [InvoiceItemInline]
    readonly_fields = ('invoice_no', 'subtotal', 'cgst_amount', 'sgst_amount', 'round_off', 'total_amount', 'created_at')

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.recalculate()


@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'state', 'gstin', 'phone')
    search_fields = ('name', 'gstin', 'city')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('party', 'invoice', 'amount', 'date', 'mode', 'reference_no')
    list_filter = ('mode', 'date')
    search_fields = ('party__name', 'reference_no')


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ('description', 'invoice', 'qty', 'unit', 'rate', 'line_total')
    search_fields = ('description', 'invoice__invoice_no')
