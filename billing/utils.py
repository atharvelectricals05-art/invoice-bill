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
