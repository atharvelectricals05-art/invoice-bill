from django import template
from billing.utils import amount_in_words as _aiw, get_party_balance

register = template.Library()


@register.filter
def inwords(value):
    """{{ invoice.total_amount|inwords }}"""
    try:
        return _aiw(value)
    except Exception:
        return ''


@register.simple_tag
def party_balance(party):
    return get_party_balance(party)


@register.filter
def currency(value):
    """Format value as ₹1,23,456.00 (Indian formatting)."""
    try:
        from decimal import Decimal
        value = Decimal(str(value))
        # Basic Indian formatting
        val_str = f'{value:,.2f}'
        return f'₹{val_str}'
    except Exception:
        return value


@register.filter
def subtract(value, arg):
    try:
        return value - arg
    except Exception:
        return 0


@register.filter
def status_badge(status):
    mapping = {
        'paid': 'success',
        'partial': 'warning',
        'unpaid': 'danger',
    }
    return mapping.get(status, 'secondary')
