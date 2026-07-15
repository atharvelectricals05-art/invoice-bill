"""
Seed command — populates demo data so the dashboard isn't empty on first run.
Run with: python manage.py seed_data
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Seed demo data: CompanyProfile, Parties, Invoices, Payments'

    def handle(self, *args, **options):
        from billing.models import CompanyProfile, Party, Invoice, InvoiceItem, Payment

        self.stdout.write('Seeding data...')

        # ── Company Profile ───────────────────────────────────────────────────
        company, created = CompanyProfile.objects.update_or_create(
            pk=1,
            defaults={
                'name': 'Atharva Electricals',
                'formerly_known_as': '',
                'address': '123, Electrical Market, Industrial Area, Mumbai - 400001',
                'phone': '+91-22-12345678',
                'email': 'info@atharvaelectricals.com',
                'gstin': '27AABCA1234A1Z5',
                'pan': 'AABCA1234A',
                'bank_name': 'State Bank of India',
                'bank_branch': 'Industrial Area Branch',
                'bank_account_no': '1234567890',
                'neft_ifsc': 'SBIN0001234',
                'msme_no': 'UDYAM-MH-01-0001234',
            }
        )
        action = 'Created' if created else 'Updated'
        self.stdout.write(f'  {action} CompanyProfile: {company.name}')

        # ── Parties ───────────────────────────────────────────────────────────
        parties_data = [
            {
                'name': 'Bright Cables Pvt. Ltd.',
                'address': '45 Cable Road, Thane',
                'city': 'Thane',
                'state': 'Maharashtra',
                'state_code': '27',
                'gstin': '27AAABC1234B1Z1',
                'contact_person': 'Ramesh Joshi',
                'phone': '9876543210',
            },
            {
                'name': 'Sunrise Electricals',
                'address': 'Shop 7, Electrical Complex, Pune',
                'city': 'Pune',
                'state': 'Maharashtra',
                'state_code': '27',
                'gstin': '27BBBDE5678C1Z2',
                'contact_person': 'Sunil Patil',
                'phone': '9765432109',
            },
            {
                'name': 'Power Tech Solutions',
                'address': 'B-12, MIDC, Navi Mumbai',
                'city': 'Navi Mumbai',
                'state': 'Maharashtra',
                'state_code': '27',
                'gstin': '27CCCFG9012D1Z3',
                'contact_person': 'Anita Sharma',
                'phone': '9654321098',
            },
        ]

        parties = []
        for pd in parties_data:
            p, created = Party.objects.get_or_create(
                name=pd['name'],
                defaults=pd,
            )
            parties.append(p)
            action = 'Created' if created else 'Exists'
            self.stdout.write(f'  {action} Party: {p.name}')

        # ── Invoices ──────────────────────────────────────────────────────────
        if Invoice.objects.count() == 0:
            # Invoice 1
            inv1 = Invoice.objects.create(
                party=parties[0],
                date=timezone.localdate().replace(day=5),
                place_of_supply='Maharashtra',
                order_number='PO-001',
            )
            items1 = [
                {
                    'description': 'Electrical Cable 1.5 sq mm',
                    'hsn_code': '85444999',
                    'make': 'MAKE - Polycab',
                    'qty': Decimal('100'),
                    'unit': 'MTR',
                    'rate': Decimal('35.00'),
                    'discount': Decimal('0'),
                    'cgst_rate': Decimal('9'),
                    'sgst_rate': Decimal('9'),
                },
                {
                    'description': 'MCB 32A Single Pole',
                    'hsn_code': '85362000',
                    'make': 'MAKE - Legrand',
                    'qty': Decimal('10'),
                    'unit': 'NOS',
                    'rate': Decimal('285.00'),
                    'discount': Decimal('50'),
                    'cgst_rate': Decimal('9'),
                    'sgst_rate': Decimal('9'),
                },
                {
                    'description': 'PVC Conduit Pipe 25mm x 3m',
                    'hsn_code': '39172100',
                    'make': 'MAKE - RR Kabel',
                    'qty': Decimal('20'),
                    'unit': 'NOS',
                    'rate': Decimal('125.00'),
                    'discount': Decimal('0'),
                    'cgst_rate': Decimal('9'),
                    'sgst_rate': Decimal('9'),
                },
            ]
            for item_data in items1:
                InvoiceItem.objects.create(invoice=inv1, **item_data)
            inv1.recalculate()
            self.stdout.write(f'  Created Invoice: {inv1.invoice_no}')

            # Invoice 2
            inv2 = Invoice.objects.create(
                party=parties[1],
                date=timezone.localdate().replace(day=12),
                place_of_supply='Maharashtra',
                order_number='PO-002',
            )
            items2 = [
                {
                    'description': '3M Electrical Insulation Tape',
                    'hsn_code': '39191090',
                    'make': 'MAKE - 3M',
                    'qty': Decimal('50'),
                    'unit': 'NOS',
                    'rate': Decimal('45.00'),
                    'discount': Decimal('0'),
                    'cgst_rate': Decimal('9'),
                    'sgst_rate': Decimal('9'),
                },
                {
                    'description': 'LED Downlight 12W Round',
                    'hsn_code': '94054090',
                    'make': 'MAKE - Philips',
                    'qty': Decimal('25'),
                    'unit': 'NOS',
                    'rate': Decimal('320.00'),
                    'discount': Decimal('100'),
                    'cgst_rate': Decimal('9'),
                    'sgst_rate': Decimal('9'),
                },
            ]
            for item_data in items2:
                InvoiceItem.objects.create(invoice=inv2, **item_data)
            inv2.recalculate()
            self.stdout.write(f'  Created Invoice: {inv2.invoice_no}')

            # Invoice 3
            inv3 = Invoice.objects.create(
                party=parties[2],
                date=timezone.localdate(),
                place_of_supply='Maharashtra',
            )
            items3 = [
                {
                    'description': 'Industrial Socket 20A 3-Pin',
                    'hsn_code': '85366990',
                    'make': 'MAKE - Havells',
                    'qty': Decimal('15'),
                    'unit': 'NOS',
                    'rate': Decimal('485.00'),
                    'discount': Decimal('0'),
                    'cgst_rate': Decimal('9'),
                    'sgst_rate': Decimal('9'),
                },
                {
                    'description': 'Distribution Board 8-Way',
                    'hsn_code': '85362000',
                    'make': 'MAKE - Schneider',
                    'qty': Decimal('3'),
                    'unit': 'NOS',
                    'rate': Decimal('1850.00'),
                    'discount': Decimal('200'),
                    'cgst_rate': Decimal('9'),
                    'sgst_rate': Decimal('9'),
                },
            ]
            for item_data in items3:
                InvoiceItem.objects.create(invoice=inv3, **item_data)
            inv3.recalculate()
            self.stdout.write(f'  Created Invoice: {inv3.invoice_no}')

            # ── Payments ──────────────────────────────────────────────────────
            Payment.objects.create(
                party=parties[0],
                invoice=inv1,
                amount=Decimal('5000.00'),
                date=timezone.localdate(),
                mode='NEFT/RTGS',
                reference_no='NEFT2024001',
                notes='Advance payment',
            )
            self.stdout.write(f'  Created Payment for {parties[0].name}')

            Payment.objects.create(
                party=parties[1],
                invoice=inv2,
                amount=inv2.total_amount,
                date=timezone.localdate(),
                mode='Cheque',
                reference_no='CHQ-456789',
                notes='Full payment by cheque',
            )
            self.stdout.write(f'  Created Payment for {parties[1].name} (full settlement)')
        else:
            self.stdout.write('  Invoices already exist, skipping invoice/payment seed.')

        self.stdout.write(self.style.SUCCESS('\nSeed data loaded successfully!'))
        self.stdout.write('  Create a superuser with: python manage.py createsuperuser')
