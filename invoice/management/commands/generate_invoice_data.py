"""
Management command to generate random test data for invoice system
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from decimal import Decimal
import random
import string
from datetime import datetime, timedelta

from invoice.models import Invoice, InvoiceItem, InvoiceSequence
from customer.models import Customer
from inventory.models import ProductVariant

User = get_user_model()


class Command(BaseCommand):
    help = 'Generate random test data for invoice system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--invoices',
            type=int,
            default=300,
            help='Number of invoices to create (default: 300)'
        )
        parser.add_argument(
            '--items-per-invoice',
            type=int,
            default=3,
            help='Average items per invoice (default: 3)'
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing test data before creating new data'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without making changes'
        )

    def handle(self, *args, **options):
        invoices_count = options['invoices']
        items_per_invoice = options['items_per_invoice']
        clear_existing = options['clear_existing']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
            self._show_preview(invoices_count, items_per_invoice)
            return

        # Check dependencies
        if not Customer.objects.exists():
            self.stdout.write(
                self.style.ERROR('No customers found! Please create customers first.')
            )
            return

        if not ProductVariant.objects.exists():
            self.stdout.write(
                self.style.ERROR('No product variants found! Please create inventory data first.')
            )
            return

        if clear_existing:
            self._clear_existing_data()

        # Create invoice sequences
        self._create_invoice_sequences()

        # Create invoices and items
        invoices = self._create_invoices_and_items(invoices_count, items_per_invoice)

        self.stdout.write(
            self.style.SUCCESS(f'Successfully generated invoice test data!')
        )

    def _show_preview(self, invoices_count, items_per_invoice):
        """Show preview of what will be created"""
        total_items = invoices_count * items_per_invoice
        
        self.stdout.write(f'Will create:')
        self.stdout.write(f'  - {invoices_count} Invoices')
        self.stdout.write(f'  - ~{total_items} Invoice Items')
        self.stdout.write(f'  - Various payment types (Cash/Credit)')
        self.stdout.write(f'  - Different invoice types (GST/Cash)')
        self.stdout.write(f'  - Realistic pricing and discounts')
        self.stdout.write(f'  - Invoice sequences for multiple financial years')

    def _clear_existing_data(self):
        """Clear existing test data"""
        self.stdout.write('Clearing existing test data...')
        
        with transaction.atomic():
            InvoiceItem.objects.all().delete()
            Invoice.objects.all().delete()
            InvoiceSequence.objects.all().delete()
            
        self.stdout.write('Existing data cleared.')

    def _create_invoice_sequences(self):
        """Create invoice sequences for different financial years"""
        self.stdout.write('Creating invoice sequences...')
        
        # Get current and previous financial years
        current_year = datetime.now().year
        financial_years = []
        
        for year in range(current_year - 2, current_year + 1):
            fy = f"{year}-{str(year + 1)[2:]}"
            financial_years.append(fy)
        
        # Create sequences for both invoice types
        invoice_types = [Invoice.Invoice_type.GST, Invoice.Invoice_type.CASH]
        
        for fy in financial_years:
            for invoice_type in invoice_types:
                InvoiceSequence.objects.get_or_create(
                    invoice_type=invoice_type,
                    financial_year=fy,
                    defaults={'last_number': 0}
                )
        
        self.stdout.write('Invoice sequences created successfully!')

    def _create_invoices_and_items(self, invoices_count, items_per_invoice):
        """Create invoices with realistic data and invoice items"""
        self.stdout.write(f'Creating {invoices_count} invoices...')
        
        # Get existing customers and product variants
        customers = list(Customer.objects.all())
        product_variants = list(ProductVariant.objects.all())
        
        # Invoice types and payment types
        invoice_types = [Invoice.Invoice_type.GST, Invoice.Invoice_type.CASH]
        payment_types = [Invoice.PaymentType.CASH, Invoice.PaymentType.CREDIT]
        payment_methods = [
            Invoice.PaymentMethod.CASH,
            Invoice.PaymentMethod.CHEQUE,
            Invoice.PaymentMethod.CASH_ON_DELIVERY,
            Invoice.PaymentMethod.CREDIT_CARD,
            Invoice.PaymentMethod.DEBIT_CARD,
            Invoice.PaymentMethod.UPI,
            Invoice.PaymentMethod.ONLINE_PAYMENT,
            Invoice.PaymentMethod.OTHER
        ]
        
        # Notes templates
        notes_templates = [
            "Regular customer purchase",
            "Bulk order discount applied",
            "Seasonal sale purchase",
            "Corporate order",
            "Retail purchase",
            "Wholesale transaction",
            "Special pricing for loyal customer",
            "End of season clearance",
            "New customer welcome discount",
            "Referral bonus applied",
            "Cash payment discount",
            "Credit terms: 30 days",
            "Advance payment received",
            "Partial payment invoice",
            "Return and exchange processed",
            "Festival season sale",
            "Clearance sale item",
            "VIP customer pricing",
            "Volume discount applied",
            "Early payment discount"
        ]
        
        created_invoices = []
        user = self._get_or_create_user()
        
        for i in range(invoices_count):
            # Select random customer
            customer = random.choice(customers)
            
            # Invoice type (mostly GST invoices)
            invoice_type = random.choices(
                invoice_types, 
                weights=[80, 20]  # 80% GST, 20% CASH
            )[0]
            
            # Payment type (mostly cash payments)
            payment_type = random.choices(
                payment_types,
                weights=[70, 30]  # 70% cash, 30% credit
            )[0]
            
            # Payment method
            payment_method = random.choice(payment_methods)
            
            # Invoice date (within last 2 years)
            days_ago = random.randint(1, 730)
            invoice_date = datetime.now() - timedelta(days=days_ago)
            
            # Due date for credit invoices
            due_date = None
            if payment_type == Invoice.PaymentType.CREDIT:
                due_days = random.randint(15, 60)  # 15-60 days credit
                due_date = invoice_date + timedelta(days=due_days)
            
            # Notes
            notes = random.choice(notes_templates)
            
            # Create invoice with individual transaction
            try:
                with transaction.atomic():
                    # Create invoice without amount first (will be updated later)
                    invoice = Invoice.objects.create(
                        customer=customer,
                        invoice_type=invoice_type,
                        payment_type=payment_type,
                        payment_method=payment_method,
                        invoice_date=invoice_date,
                        due_date=due_date,
                        notes=notes,
                        created_by=user,
                        amount=Decimal('0')  # Start with 0, will be updated
                    )
                    
                    # Create invoice items
                    num_items = random.randint(1, items_per_invoice * 2)
                    total_amount = Decimal('0')
                    
                    # Select unique product variants for this invoice
                    selected_variants = random.sample(
                        product_variants, 
                        min(num_items, len(product_variants))
                    )
                    
                    for variant in selected_variants:
                        # Quantity (realistic ranges)
                        quantity = Decimal(str(random.randint(1, 10)))
                        
                        # Pricing
                        mrp = variant.mrp
                        purchase_price = variant.purchase_price
                        
                        # Unit price (with discount from MRP)
                        discount_percentage = random.randint(0, 30)  # 0-30% discount
                        unit_price = mrp * (1 - Decimal(str(discount_percentage / 100)))
                        
                        # Create invoice item
                        invoice_item = InvoiceItem.objects.create(
                            invoice=invoice,
                            product_variant=variant,
                            quantity=quantity,
                            mrp=mrp,
                            unit_price=unit_price,
                            purchase_price=purchase_price,
                            notes=f"Item for invoice {invoice.invoice_number}"
                        )
                        
                        total_amount += invoice_item.net_amount
                    
                    # Update invoice amount
                    invoice.amount = total_amount
                    
                    # Discount amount (some invoices have discounts)
                    if random.random() > 0.7:  # 30% of invoices have discounts
                        discount_percentage = random.randint(5, 20)  # 5-20% discount
                        invoice.discount_amount = total_amount * Decimal(str(discount_percentage / 100))
                    
                    # Advance amount for credit invoices
                    if payment_type == Invoice.PaymentType.CREDIT and random.random() > 0.6:
                        advance_percentage = random.randint(10, 50)  # 10-50% advance
                        invoice.advance_amount = invoice.total_payable * Decimal(str(advance_percentage / 100))
                    
                    # Paid amount (some invoices are partially paid)
                    if payment_type == Invoice.PaymentType.CREDIT:
                        if random.random() > 0.4:  # 60% of credit invoices have some payment
                            paid_percentage = random.randint(20, 100)
                            max_payable = invoice.total_payable - invoice.advance_amount
                            invoice.paid_amount = min(
                                max_payable * Decimal(str(paid_percentage / 100)),
                                max_payable
                            )
                    
                    # Update payment status
                    invoice._update_payment_status()
                    invoice.save()
                    
                    created_invoices.append(invoice)
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error creating invoice {i+1}: {e}")
                )
                import traceback
                traceback.print_exc()
                continue
            
            if (i + 1) % 30 == 0:
                self.stdout.write(f'Created {i + 1} invoices...')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {len(created_invoices)} invoices!')
        )
        return created_invoices

    def _get_or_create_user(self):
        """Get or create a user for created_by fields"""
        try:
            return User.objects.first()
        except:
            return None
