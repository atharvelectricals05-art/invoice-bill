"""
Views for the Atharva billing application.
"""
import json
from decimal import Decimal
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Sum, Count, Q, F, DecimalField
from django.db.models.functions import Coalesce
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, View,
)

from .forms import (
    InvoiceForm, InvoiceItemFormSet, PaymentForm, PartyForm,
    DateRangeFilterForm, CompanyProfileForm,
)
from .models import Invoice, InvoiceItem, Payment, Party, CompanyProfile
from .utils import (
    get_party_balance, get_party_balances_bulk, invoice_status_from_totals, amount_in_words,
)

# Reused wherever we need each invoice's payments total without a per-row query.
_WITH_RECEIVED = Coalesce(Sum('payments__amount'), Decimal('0'), output_field=DecimalField())


# ── Helpers ────────────────────────────────────────────────────────────────────

def _apply_invoice_filters(qs, form):
    if form.is_valid():
        if form.cleaned_data.get('date_from'):
            qs = qs.filter(date__gte=form.cleaned_data['date_from'])
        if form.cleaned_data.get('date_to'):
            qs = qs.filter(date__lte=form.cleaned_data['date_to'])
        if form.cleaned_data.get('q'):
            q = form.cleaned_data['q']
            qs = qs.filter(Q(invoice_no__icontains=q) | Q(party__name__icontains=q))
        if form.cleaned_data.get('party'):
            qs = qs.filter(party=form.cleaned_data['party'])
    return qs


# ── Dashboard ──────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    filter_form = DateRangeFilterForm(request.GET or None)

    # Default to current financial year
    today = timezone.localdate()
    fy_start = date(today.year if today.month >= 4 else today.year - 1, 4, 1)
    date_from = fy_start
    date_to = today

    if filter_form.is_valid():
        date_from = filter_form.cleaned_data.get('date_from') or fy_start
        date_to = filter_form.cleaned_data.get('date_to') or today

    invoices_qs = Invoice.objects.filter(date__gte=date_from, date__lte=date_to)
    payments_qs = Payment.objects.filter(date__gte=date_from, date__lte=date_to)

    total_invoiced = invoices_qs.aggregate(t=Sum('total_amount'))['t'] or Decimal('0')
    total_received = payments_qs.aggregate(t=Sum('amount'))['t'] or Decimal('0')
    total_outstanding = total_invoiced - total_received
    total_tax = invoices_qs.aggregate(
        t=Sum('cgst_amount') + Sum('sgst_amount')
    )['t'] or Decimal('0')
    # Aggregate tax correctly
    cgst_total = invoices_qs.aggregate(t=Sum('cgst_amount'))['t'] or Decimal('0')
    sgst_total = invoices_qs.aggregate(t=Sum('sgst_amount'))['t'] or Decimal('0')
    total_tax = cgst_total + sgst_total

    # Monthly chart data — last 12 months.
    # Compute the 12 (month_start, month_end, label) windows first, then pull
    # all invoices/payments spanning the whole range in 2 queries and sum
    # them in Python — instead of 24 separate DB round-trips (1 per month).
    months = []
    for i in range(11, -1, -1):
        ref = today.replace(day=1) - timedelta(days=i * 28)
        month_start = ref.replace(day=1)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(days=1)
        months.append((month_start, month_end, month_start.strftime('%b %Y')))

    range_start = months[0][0]
    range_end = months[-1][1]
    invoices_range = list(
        Invoice.objects.filter(date__gte=range_start, date__lte=range_end).values('date', 'total_amount')
    )
    payments_range = list(
        Payment.objects.filter(date__gte=range_start, date__lte=range_end).values('date', 'amount')
    )

    monthly_labels = []
    monthly_invoiced = []
    monthly_received = []
    for month_start, month_end, label in months:
        inv = sum(
            (r['total_amount'] for r in invoices_range if month_start <= r['date'] <= month_end),
            Decimal('0'),
        )
        rec = sum(
            (r['amount'] for r in payments_range if month_start <= r['date'] <= month_end),
            Decimal('0'),
        )
        monthly_labels.append(label)
        monthly_invoiced.append(float(inv))
        monthly_received.append(float(rec))

    # Top 10 parties by invoiced amount
    top_parties = (
        Party.objects.annotate(invoiced=Sum('invoices__total_amount'))
        .exclude(invoiced__isnull=True)
        .order_by('-invoiced')[:10]
    )
    top_party_labels = [p.name for p in top_parties]
    top_party_data = [float(p.invoiced or 0) for p in top_parties]

    # Party-wise outstanding
    all_parties = list(Party.objects.all())
    balances_by_party = get_party_balances_bulk(all_parties)
    party_balances = [
        {'party': p, **balances_by_party[p.pk]}
        for p in all_parties
        if balances_by_party[p.pk]['outstanding'] != 0
    ]
    party_balances.sort(key=lambda x: x['outstanding'], reverse=True)

    context = {
        'filter_form': filter_form,
        'date_from': date_from,
        'date_to': date_to,
        'total_invoiced': total_invoiced,
        'total_received': total_received,
        'total_outstanding': total_outstanding,
        'total_tax': total_tax,
        'monthly_labels': json.dumps(monthly_labels),
        'monthly_invoiced': json.dumps(monthly_invoiced),
        'monthly_received': json.dumps(monthly_received),
        'top_party_labels': json.dumps(top_party_labels),
        'top_party_data': json.dumps(top_party_data),
        'party_balances': party_balances,
    }
    return render(request, 'billing/dashboard.html', context)


# ── Party Views ────────────────────────────────────────────────────────────────

@login_required
def party_list(request):
    parties = list(Party.objects.all())
    balances_by_party = get_party_balances_bulk(parties)
    party_data = [{'party': p, **balances_by_party[p.pk]} for p in parties]
    party_data.sort(key=lambda x: x['outstanding'], reverse=True)
    return render(request, 'billing/party_list.html', {'party_data': party_data})


@login_required
def party_detail(request, pk):
    party = get_object_or_404(Party, pk=pk)
    invoices = party.invoices.annotate(total_received=_WITH_RECEIVED).order_by('-date')
    invoice_rows = [
        {
            'invoice': inv,
            'outstanding': inv.total_amount - inv.total_received,
            'status': invoice_status_from_totals(inv.total_amount, inv.total_received),
        }
        for inv in invoices
    ]
    payments = party.payments.select_related('invoice').order_by('-date')
    balance = get_party_balance(party)
    return render(request, 'billing/party_detail.html', {
        'party': party,
        'invoice_rows': invoice_rows,
        'payments': payments,
        **balance,
    })


@login_required
def party_create(request):
    if request.method == 'POST':
        form = PartyForm(request.POST)
        if form.is_valid():
            party = form.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'id': party.pk, 'name': party.name})
            messages.success(request, f'Party "{party.name}" created.')
            return redirect('billing:party_list')
    else:
        form = PartyForm()
    return render(request, 'billing/party_form.html', {'form': form, 'title': 'Add Party'})


@login_required
def party_edit(request, pk):
    party = get_object_or_404(Party, pk=pk)
    if request.method == 'POST':
        form = PartyForm(request.POST, instance=party)
        if form.is_valid():
            form.save()
            messages.success(request, f'Party "{party.name}" updated.')
            return redirect('billing:party_detail', pk=party.pk)
    else:
        form = PartyForm(instance=party)
    return render(request, 'billing/party_form.html', {'form': form, 'title': 'Edit Party', 'party': party})


# ── Invoice Views ──────────────────────────────────────────────────────────────

@login_required
def invoice_list(request):
    # total_received is annotated here (1 extra JOIN+SUM in the same query)
    # instead of calling inv.get_outstanding()/get_status() per row, which
    # would each re-query payments — 2-3 extra round-trips x 25 rows/page.
    qs = Invoice.objects.select_related('party').annotate(
        total_received=_WITH_RECEIVED
    ).order_by('-date', '-_seq')
    filter_form = DateRangeFilterForm(request.GET or None)
    qs = _apply_invoice_filters(qs, filter_form)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    invoice_rows = [
        {
            'invoice': inv,
            'outstanding': inv.total_amount - inv.total_received,
            'status': invoice_status_from_totals(inv.total_amount, inv.total_received),
        }
        for inv in page_obj
    ]

    return render(request, 'billing/invoice_list.html', {
        'filter_form': filter_form,
        'invoice_rows': invoice_rows,
        'page_obj': page_obj,
    })


@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice.objects.select_related('party'), pk=pk)
    company = CompanyProfile.get_solo()
    items = invoice.items.all()
    payments = invoice.payments.all()
    received = invoice.get_total_received()
    outstanding = invoice.total_amount - received
    status = invoice_status_from_totals(invoice.total_amount, received)
    amount_words = amount_in_words(invoice.total_amount)
    return render(request, 'billing/invoice_detail.html', {
        'invoice': invoice,
        'company': company,
        'items': items,
        'payments': payments,
        'received': received,
        'outstanding': outstanding,
        'status': status,
        'amount_words': amount_words,
    })


@login_required
@transaction.atomic
def invoice_create(request):
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        formset = InvoiceItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            invoice = form.save(commit=False)
            # Allow manual invoice_no override
            if not invoice.invoice_no:
                from django.db.models import Max
                last = Invoice.objects.aggregate(max_no=Max('_seq'))['max_no'] or 0
                invoice._seq = last + 1
                invoice.invoice_no = f'ISL-{invoice._seq:06d}'
            invoice.save()
            formset.instance = invoice
            formset.save()
            invoice.recalculate()
            messages.success(request, f'Invoice {invoice.invoice_no} created.')
            return redirect('billing:invoice_detail', pk=invoice.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = InvoiceForm()
        formset = InvoiceItemFormSet()

    parties = Party.objects.order_by('name').values('id', 'name')
    return render(request, 'billing/invoice_form.html', {
        'form': form,
        'formset': formset,
        'parties_json': json.dumps(list(parties)),
        'title': 'Create Invoice',
    })


@login_required
@transaction.atomic
def invoice_edit(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice)
        formset = InvoiceItemFormSet(request.POST, instance=invoice)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            invoice.recalculate()
            messages.success(request, f'Invoice {invoice.invoice_no} updated.')
            return redirect('billing:invoice_detail', pk=invoice.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = InvoiceForm(instance=invoice)
        formset = InvoiceItemFormSet(instance=invoice)

    parties = Party.objects.order_by('name').values('id', 'name')
    return render(request, 'billing/invoice_form.html', {
        'form': form,
        'formset': formset,
        'invoice': invoice,
        'parties_json': json.dumps(list(parties)),
        'title': f'Edit Invoice {invoice.invoice_no}',
    })


# ── PDF View ───────────────────────────────────────────────────────────────────

@login_required
def invoice_pdf(request, pk):
    invoice = get_object_or_404(Invoice.objects.select_related('party'), pk=pk)
    company = CompanyProfile.get_solo()
    items = list(invoice.items.all())
    amount_words = amount_in_words(invoice.total_amount)

    # Filler rows to keep the item table tall enough (like the sample invoice)
    filler_count = max(0, 8 - len(items))
    filler_rows = range(filler_count)

    from django.template.loader import render_to_string
    from io import BytesIO
    from xhtml2pdf import pisa
    import os

    def link_callback(uri, rel):
        """Allow xhtml2pdf to find media/static files on disk."""
        from django.conf import settings
        # Handle media files (logos)
        if uri.startswith(settings.MEDIA_URL):
            path = os.path.join(
                settings.MEDIA_ROOT,
                uri.replace(settings.MEDIA_URL, '').lstrip('/'),
            )
            if os.path.isfile(path):
                return path
        # Handle static files. STATIC_ROOT is only populated after
        # `collectstatic` (production build step) and its filenames are
        # content-hashed by ManifestStaticFilesStorage, so `{% static %}`
        # already points there correctly once deployed. Locally (no
        # collectstatic run yet), fall back to the source STATICFILES_DIRS
        # so static images still resolve during development.
        if uri.startswith(settings.STATIC_URL):
            rel_path = uri.replace(settings.STATIC_URL, '').lstrip('/')
            candidates = [settings.STATIC_ROOT] if settings.STATIC_ROOT else []
            candidates += list(settings.STATICFILES_DIRS)
            for root in candidates:
                path = os.path.join(root, rel_path)
                if os.path.isfile(path):
                    return path
        return uri

    # Total quantity for the totals row
    total_qty = sum(item.qty for item in items)

    html_string = render_to_string('billing/invoice_pdf.html', {
        'invoice': invoice,
        'company': company,
        'items': items,
        'filler_rows': filler_rows,
        'total_qty': total_qty,
        'amount_words': amount_words,
        'request': request,
    })

    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(
        html_string,
        dest=buffer,
        encoding='utf-8',
        link_callback=link_callback,
    )

    if pisa_status.err:
        return HttpResponse(
            f'<h3>PDF generation failed</h3><pre>{pisa_status.err}</pre>',
            status=500,
        )

    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Invoice-{invoice.invoice_no}.pdf"'
    return response


# ── Payment Views ──────────────────────────────────────────────────────────────

@login_required
def payment_list(request):
    qs = Payment.objects.select_related('party', 'invoice').order_by('-date')
    filter_form = DateRangeFilterForm(request.GET or None)
    if filter_form.is_valid():
        if filter_form.cleaned_data.get('date_from'):
            qs = qs.filter(date__gte=filter_form.cleaned_data['date_from'])
        if filter_form.cleaned_data.get('date_to'):
            qs = qs.filter(date__lte=filter_form.cleaned_data['date_to'])
        if filter_form.cleaned_data.get('q'):
            q = filter_form.cleaned_data['q']
            qs = qs.filter(Q(party__name__icontains=q) | Q(reference_no__icontains=q))
        if filter_form.cleaned_data.get('party'):
            qs = qs.filter(party=filter_form.cleaned_data['party'])

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'billing/payment_list.html', {
        'filter_form': filter_form,
        'page_obj': page_obj,
    })


@login_required
def payment_create(request):
    invoice_id = request.GET.get('invoice')
    party_id = request.GET.get('party')

    initial = {}
    if invoice_id:
        try:
            inv = Invoice.objects.get(pk=invoice_id)
            initial['invoice'] = inv
            initial['party'] = inv.party
            initial['amount'] = inv.get_outstanding()
        except Invoice.DoesNotExist:
            pass

    if request.method == 'POST':
        form = PaymentForm(request.POST, party_id=party_id)
        if form.is_valid():
            payment = form.save()
            messages.success(request, f'Payment of ₹{payment.amount} recorded.')
            if invoice_id:
                return redirect('billing:invoice_detail', pk=invoice_id)
            return redirect('billing:payment_list')
    else:
        form = PaymentForm(initial=initial, party_id=party_id)

    return render(request, 'billing/payment_form.html', {'form': form})


@login_required
def party_invoices(request):
    """AJAX: return unpaid/partial invoices for a given party as JSON."""
    party_id = request.GET.get('party_id')
    invoices = (
        Invoice.objects.filter(party_id=party_id).annotate(total_received=_WITH_RECEIVED).order_by('-date')
        if party_id else Invoice.objects.none()
    )
    data = [
        {'id': inv.pk, 'text': f'{inv.invoice_no} — ₹{inv.total_amount - inv.total_received} outstanding'}
        for inv in invoices
    ]
    return JsonResponse({'invoices': data})


# ── Company Profile ────────────────────────────────────────────────────────────

@login_required
def company_profile(request):
    company = CompanyProfile.get_solo()
    if request.method == 'POST':
        form = CompanyProfileForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Company profile updated.')
            return redirect('billing:company_profile')
    else:
        form = CompanyProfileForm(instance=company)
    return render(request, 'billing/company_profile.html', {'form': form, 'company': company})


# ── Root redirect ──────────────────────────────────────────────────────────────

@login_required
def index(request):
    return redirect('billing:dashboard')
