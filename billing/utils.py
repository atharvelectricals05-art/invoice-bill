"""
Business logic utilities for the billing app.
"""
from decimal import Decimal
from django.db.models import Sum


# ── Indian amount in words ─────────────────────────────────────────────────────

ONES = [
    '', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
    'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
    'Seventeen', 'Eighteen', 'Nineteen',
]
TENS = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']


def _two_digits(n):
    if n < 20:
        return ONES[n]
    return (TENS[n // 10] + (' ' + ONES[n % 10] if n % 10 else '')).strip()


def _three_digits(n):
    if n == 0:
        return ''
    h = n // 100
    remainder = n % 100
    parts = []
    if h:
        parts.append(ONES[h] + ' Hundred')
    if remainder:
        parts.append(_two_digits(remainder))
    return ' '.join(parts)


def amount_in_words(amount):
    """Convert a decimal/integer amount to Indian words with rupees and paise."""
    amount = Decimal(str(amount))
    rupees = int(amount)
    paise = int(round((amount - rupees) * 100))

    if rupees == 0 and paise == 0:
        return 'Zero Rupees Only'

    parts = []
    cr = rupees // 10_000_000
    rupees %= 10_000_000
    lac = rupees // 100_000
    rupees %= 100_000
    th = rupees // 1_000
    rupees %= 1_000
    hu = rupees

    if cr:
        parts.append(_three_digits(cr) + ' Crore')
    if lac:
        parts.append(_three_digits(lac) + ' Lakh')
    if th:
        parts.append(_three_digits(th) + ' Thousand')
    if hu:
        parts.append(_three_digits(hu))

    rupees_words = ' '.join(parts).strip()
    result = f'{rupees_words} Rupees'
    if paise:
        result += f' and {_two_digits(paise)} Paise'
    return result + ' Only'


# ── Party balance helper ───────────────────────────────────────────────────────

def get_party_balance(party):
    """Return dict: total_invoiced, total_received, outstanding."""
    total_invoiced = party.invoices.aggregate(t=Sum('total_amount'))['t'] or Decimal('0')
    total_received = party.payments.aggregate(t=Sum('amount'))['t'] or Decimal('0')
    outstanding = total_invoiced - total_received
    return {
        'total_invoiced': total_invoiced,
        'total_received': total_received,
        'outstanding': outstanding,
    }


def invoice_status_from_totals(total_amount, total_received):
    """Same thresholds as Invoice.get_status(), computed from an already-fetched
    total_received instead of issuing a fresh payments query per invoice."""
    from .models import Invoice

    total_received = total_received or Decimal('0')
    outstanding = total_amount - total_received
    if outstanding <= 0:
        return Invoice.STATUS_PAID
    elif total_received > 0:
        return Invoice.STATUS_PARTIAL
    return Invoice.STATUS_UNPAID


def get_party_balances_bulk(parties):
    """Same result as calling get_party_balance() per party, but for a whole
    list of parties in 2 queries total instead of 2*N (avoids the N+1 that
    made the dashboard/party list take 15-20s with real network latency)."""
    from .models import Invoice, Payment

    party_ids = [p.pk for p in parties]
    invoiced_map = dict(
        Invoice.objects.filter(party_id__in=party_ids)
        .values('party_id').annotate(t=Sum('total_amount'))
        .values_list('party_id', 't')
    )
    received_map = dict(
        Payment.objects.filter(party_id__in=party_ids)
        .values('party_id').annotate(t=Sum('amount'))
        .values_list('party_id', 't')
    )
    balances = {}
    for p in parties:
        total_invoiced = invoiced_map.get(p.pk) or Decimal('0')
        total_received = received_map.get(p.pk) or Decimal('0')
        balances[p.pk] = {
            'total_invoiced': total_invoiced,
            'total_received': total_received,
            'outstanding': total_invoiced - total_received,
        }
    return balances
