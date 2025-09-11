"""
Management command to generate random test data for customer system
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from decimal import Decimal
import random
import string
from datetime import datetime, timedelta

from customer.models import Customer, Payment

User = get_user_model()


class Command(BaseCommand):
    help = 'Generate random test data for customer system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--customers',
            type=int,
            default=200,
            help='Number of customers to create (default: 200)'
        )
        parser.add_argument(
            '--payments',
            type=int,
            default=500,
            help='Number of payments to create (default: 500)'
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
        customers_count = options['customers']
        payments_count = options['payments']
        clear_existing = options['clear_existing']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
            self._show_preview(customers_count, payments_count)
            return

        if clear_existing:
            self._clear_existing_data()

        # Create customers
        customers = self._create_customers(customers_count)
        
        # Create payments
        if customers:
            self._create_payments(customers, payments_count)

        self.stdout.write(
            self.style.SUCCESS(f'Successfully generated customer test data!')
        )

    def _show_preview(self, customers_count, payments_count):
        """Show preview of what will be created"""
        self.stdout.write(f'Will create:')
        self.stdout.write(f'  - {customers_count} Customers')
        self.stdout.write(f'  - {payments_count} Payments')
        self.stdout.write(f'  - Realistic Indian names, addresses, and phone numbers')
        self.stdout.write(f'  - Various payment methods and amounts')

    def _clear_existing_data(self):
        """Clear existing test data"""
        self.stdout.write('Clearing existing test data...')
        
        with transaction.atomic():
            Payment.objects.all().delete()
            Customer.objects.all().delete()
            
        self.stdout.write('Existing data cleared.')

    def _create_customers(self, customers_count):
        """Create customers with realistic data"""
        self.stdout.write(f'Creating {customers_count} customers...')
        
        # Indian names
        first_names = [
            'Raj', 'Priya', 'Amit', 'Sunita', 'Vikram', 'Deepa', 'Arjun', 'Kavita',
            'Rohit', 'Meera', 'Suresh', 'Anita', 'Kumar', 'Pooja', 'Vishal', 'Ritu',
            'Manish', 'Shilpa', 'Ravi', 'Neha', 'Ajay', 'Sonia', 'Nitin', 'Preeti',
            'Sanjay', 'Monika', 'Rakesh', 'Jyoti', 'Pankaj', 'Swati', 'Ashok', 'Divya',
            'Manoj', 'Rekha', 'Vinod', 'Sarita', 'Rajesh', 'Usha', 'Dinesh', 'Geeta',
            'Sandeep', 'Kamala', 'Vijay', 'Lata', 'Anil', 'Pushpa', 'Mukesh', 'Indira',
            'Harish', 'Sushila', 'Bharat', 'Kalpana', 'Girish', 'Madhu', 'Satish', 'Rama',
            'Jagdish', 'Leela', 'Kiran', 'Shanti', 'Ram', 'Ganga', 'Shyam', 'Radha',
            'Krishna', 'Sita', 'Hari', 'Parvati', 'Govind', 'Durga', 'Balram', 'Lakshmi',
            'Madhav', 'Saraswati', 'Narayan', 'Kali', 'Vishnu', 'Annapurna', 'Shiva', 'Gauri',
            'Aryan', 'Ishaan', 'Arnav', 'Vivaan', 'Aditya', 'Rudra', 'Krish', 'Shaurya',
            'Ananya', 'Ishita', 'Kavya', 'Riya', 'Saanvi', 'Aadhya', 'Pari', 'Diya',
            'Advika', 'Anika', 'Kiara', 'Myra', 'Prisha', 'Sara', 'Tara', 'Zara'
        ]
        
        last_names = [
            'Sharma', 'Verma', 'Gupta', 'Singh', 'Kumar', 'Yadav', 'Patel', 'Shah',
            'Agarwal', 'Jain', 'Malhotra', 'Chopra', 'Bansal', 'Goyal', 'Khanna', 'Saxena',
            'Tiwari', 'Mishra', 'Pandey', 'Joshi', 'Bhatt', 'Reddy', 'Nair', 'Iyer',
            'Menon', 'Pillai', 'Rao', 'Naidu', 'Das', 'Bose', 'Banerjee', 'Chatterjee',
            'Mukherjee', 'Ghosh', 'Sen', 'Roy', 'Dutta', 'Saha', 'Mondal', 'Halder',
            'Mahato', 'Soren', 'Tudu', 'Hembram', 'Murmu', 'Besra', 'Kujur', 'Topno',
            'Kapoor', 'Chandra', 'Agarwal', 'Bajaj', 'Goel', 'Lal', 'Mehta', 'Aggarwal',
            'Ahuja', 'Bhardwaj', 'Chaudhary', 'Dixit', 'Garg', 'Handa', 'Jindal', 'Khandelwal'
        ]
        
        created_customers = []
        
        with transaction.atomic():
            for i in range(customers_count):
                first_name = random.choice(first_names)
                last_name = random.choice(last_names)
                name = f"{first_name} {last_name}"
                
                # Generate unique phone
                phone_number = self._generate_unique_phone()
                
                # Generate email (optional)
                email = self._generate_email(name) if random.random() > 0.3 else None
                
                # Generate address (optional)
                address = self._generate_address() if random.random() > 0.2 else None
                
                # Store credit balance (most customers have no credit)
                store_credit_balance = Decimal('0') if random.random() > 0.8 else Decimal(str(random.randint(100, 5000)))
                
                # Referral (some customers are referred by others)
                referred_by = None
                if created_customers and random.random() > 0.7:
                    referred_by = random.choice(created_customers)
                
                # Get a user for created_by
                user = self._get_or_create_user()
                
                try:
                    customer = Customer.objects.create(
                        name=name,
                        phone_number=phone_number,
                        email=email,
                        address=address,
                        store_credit_balance=store_credit_balance,
                        referred_by=referred_by,
                        created_by=user
                    )
                    created_customers.append(customer)
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Error creating customer {name}: {e}")
                    )
                    continue
                
                if (i + 1) % 20 == 0:
                    self.stdout.write(f'Created {i + 1} customers...')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {len(created_customers)} customers!')
        )
        return created_customers

    def _create_payments(self, customers, payments_count):
        """Create payment records for customers"""
        self.stdout.write(f'Creating {payments_count} payments...')
        
        payment_methods = [
            Payment.PaymentMethod.CASH,
            Payment.PaymentMethod.BANK_TRANSFER,
            Payment.PaymentMethod.UPI,
            Payment.PaymentMethod.CHEQUE,
            Payment.PaymentMethod.CREDIT_CARD,
            Payment.PaymentMethod.DEBIT_CARD,
            Payment.PaymentMethod.ONLINE_PAYMENT
        ]
        
        payment_type_choices = [
            Payment.PaymentType.Paid,
            Payment.PaymentType.Purchased
        ]
        
        notes_templates = [
            "Payment for outstanding invoice",
            "Advance payment for future purchases",
            "Settlement of credit account",
            "Partial payment received",
            "Full payment received",
            "Refund processed",
            "Credit adjustment",
            "Cash payment at counter",
            "Online payment via UPI",
            "Bank transfer payment",
            "Cheque payment received",
            "Card payment processed",
            "Monthly installment payment",
            "Bulk purchase payment",
            "Seasonal discount payment",
            "Loyalty reward redemption"
        ]
        
        user = self._get_or_create_user()
        created_payments = []
        
        with transaction.atomic():
            for i in range(payments_count):
                customer = random.choice(customers)
                
                # Payment amount (realistic ranges)
                amount = Decimal(str(random.randint(500, 50000)))
                
                # Payment method
                method = random.choice(payment_methods)
                
                # Paid/Purchased type
                payment_type = random.choice(payment_type_choices)
                
                # Transaction ID (for non-cash payments)
                transaction_id = None
                if method != Payment.PaymentMethod.CASH:
                    transaction_id = f"TXN{random.randint(100000, 999999)}"
                
                # Payment date (within last 2 years)
                days_ago = random.randint(1, 730)
                payment_date = datetime.now() - timedelta(days=days_ago)
                
                # Notes
                notes = random.choice(notes_templates)
                
                try:
                    payment = Payment.objects.create(
                        customer=customer,
                        payment_type=payment_type,
                        amount=amount,
                        method=method,
                        transaction_id=transaction_id,
                        payment_date=payment_date,
                        notes=notes,
                        created_by=user
                    )
                    created_payments.append(payment)
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Error creating payment: {e}")
                    )
                    continue
                
                if (i + 1) % 50 == 0:
                    self.stdout.write(f'Created {i + 1} payments...')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {len(created_payments)} payments!')
        )
        return created_payments

    def _generate_unique_phone(self):
        """Generate a unique phone number"""
        while True:
            phone = ''.join(random.choices(string.digits, k=10))
            if not Customer.objects.filter(phone_number=phone).exists():
                return phone

    def _generate_email(self, name):
        """Generate email from name"""
        domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'rediffmail.com']
        name_clean = name.lower().replace(' ', '.')
        return f"{name_clean}@{random.choice(domains)}"

    def _generate_address(self):
        """Generate realistic Indian addresses"""
        areas = [
            'Sector 15', 'Raj Nagar', 'Civil Lines', 'Model Town', 'Green Park',
            'Karol Bagh', 'Connaught Place', 'Lajpat Nagar', 'Greater Kailash',
            'Vasant Kunj', 'Dwarka', 'Rohini', 'Pitampura', 'Janakpuri',
            'Paschim Vihar', 'Uttam Nagar', 'Najafgarh', 'Mukherjee Nagar',
            'Malviya Nagar', 'Hauz Khas', 'South Extension', 'Defence Colony',
            'Kalkaji', 'Govindpuri', 'Okhla', 'Jasola', 'Sarita Vihar',
            'Mayur Vihar', 'Preet Vihar', 'Shakarpur', 'Laxmi Nagar'
        ]
        
        cities = [
            'New Delhi', 'Mumbai', 'Bangalore', 'Chennai', 'Kolkata', 'Hyderabad',
            'Pune', 'Ahmedabad', 'Jaipur', 'Surat', 'Lucknow', 'Kanpur',
            'Nagpur', 'Indore', 'Thane', 'Bhopal', 'Visakhapatnam', 'Pimpri',
            'Gurgaon', 'Noida', 'Faridabad', 'Ghaziabad', 'Meerut', 'Agra',
            'Varanasi', 'Allahabad', 'Bareilly', 'Moradabad', 'Aligarh'
        ]
        
        states = [
            'Delhi', 'Maharashtra', 'Karnataka', 'Tamil Nadu', 'West Bengal',
            'Telangana', 'Gujarat', 'Rajasthan', 'Uttar Pradesh', 'Madhya Pradesh',
            'Andhra Pradesh', 'Haryana', 'Punjab', 'Bihar', 'Odisha', 'Kerala',
            'Assam', 'Jharkhand', 'Chhattisgarh', 'Himachal Pradesh', 'Uttarakhand'
        ]
        
        house_numbers = [f"{random.randint(1, 999)}/{random.randint(1, 99)}", 
                        f"{random.randint(1, 50)}-{random.randint(1, 50)}",
                        f"Flat {random.randint(1, 200)}",
                        f"House {random.randint(1, 100)}",
                        f"Villa {random.randint(1, 50)}"]
        
        area = random.choice(areas)
        city = random.choice(cities)
        state = random.choice(states)
        house = random.choice(house_numbers)
        
        return f"{house}, {area}, {city}, {state} - {random.randint(100000, 999999)}"

    def _get_or_create_user(self):
        """Get or create a user for created_by fields"""
        try:
            return User.objects.first()
        except:
            return None
