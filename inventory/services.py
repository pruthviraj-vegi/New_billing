from django.db import transaction
from .models import InventoryLog
from decimal import Decimal
from django.db.models import F


class InventoryService:
    """Service class for inventory operations"""

    @staticmethod
    def apply_discount(variant, percentage, user=None):
        """Apply discount and log the change"""
        if 0 <= percentage <= 100:
            variant.discount_percentage = percentage
            variant.save()

            InventoryLog.objects.create(
                variant=variant,
                created_by=user,
                quantity_change=0,
                new_quantity=variant.quantity,
                transaction_type=InventoryLog.TransactionTypes.ADJUSTMENT_IN,
                notes=f"Discount applied: {percentage}%",
            )

    @staticmethod
    def update_quantity(variant, change, user=None, notes="", supplier_invoice=None):
        """Safely update quantity and create log entry"""
        with transaction.atomic():
            new_quantity = variant.quantity + change
            variant.quantity = new_quantity
            variant.save()

            InventoryLog.objects.create(
                variant=variant,
                created_by=user,
                quantity_change=change,
                new_quantity=new_quantity,
                transaction_type=InventoryLog.TransactionTypes.STOCK_IN,
                total_value=change * variant.purchase_price,
                notes=notes or f"Stock In: {change} units",
                supplier_invoice=supplier_invoice,
            )

    @staticmethod
    def adjust_in_quantity(variant, change, user=None, notes=""):
        """Adjust quantity and create log entry"""
        with transaction.atomic():
            if change == 0:
                raise ValueError("Quantity change cannot be zero")

            new_quantity = variant.quantity + change
            variant.quantity = new_quantity
            variant.save()

            InventoryLog.objects.create(
                variant=variant,
                created_by=user,
                quantity_change=change,
                new_quantity=new_quantity,
                transaction_type=InventoryLog.TransactionTypes.ADJUSTMENT_IN,
                total_value=change * variant.purchase_price,
                notes=notes or f"Adjustment In: {change} units",
            )

    @staticmethod
    def adjust_out_quantity(variant, change, user=None, notes=""):
        """Adjust quantity and create log entry"""
        with transaction.atomic():
            if change == 0:
                raise ValueError("Quantity change cannot be zero")

            new_quantity = variant.quantity - change
            variant.quantity = new_quantity
            variant.save()

            InventoryLog.objects.create(
                variant=variant,
                created_by=user,
                quantity_change=-change,
                new_quantity=new_quantity,
                transaction_type=InventoryLog.TransactionTypes.ADJUSTMENT_OUT,
                total_value=change * variant.purchase_price,
                notes=notes or f"Adjustment Out: {change} units",
            )

    @staticmethod
    def create_initial_log(variant, user=None, notes="", supplier_invoice=None):
        try:
            with transaction.atomic():
                inventory_log = InventoryLog.objects.create(
                    variant=variant,
                    created_by=user,
                    quantity_change=variant.quantity,
                    new_quantity=variant.quantity,
                    purchase_price=variant.purchase_price,
                    remaining_quantity=variant.quantity,
                    mrp=variant.mrp,
                    total_value=variant.quantity * variant.purchase_price,
                    transaction_type=InventoryLog.TransactionTypes.INITIAL,
                    notes=notes or f"Initial Stock: {variant.quantity} units",
                    supplier_invoice=supplier_invoice,
                )
                return inventory_log

        except Exception as e:
            print(e)
            return None

    @staticmethod
    def update_initial_log(variant, user=None, notes="", supplier_invoice=None):
        log_data = InventoryLog.objects.filter(
            variant=variant,
            transaction_type=InventoryLog.TransactionTypes.INITIAL,
        ).first()
        if log_data:
            log_data.quantity_change = variant.quantity
            log_data.new_quantity = variant.quantity
            log_data.remaining_quantity = variant.quantity
            log_data.purchase_price = variant.purchase_price
            log_data.mrp = variant.mrp
            log_data.total_value = variant.quantity * variant.purchase_price
            log_data.notes = notes or f"Initial Stock: {variant.quantity} units"
            log_data.supplier_invoice = supplier_invoice
            log_data.created_by = user
            log_data.save()

    @staticmethod
    def update_stock_in_log(
        variant,
        quantity_change,
        user=None,
        notes="",
        supplier_invoice=None,
        purchase_price=None,
        mrp=None,
    ):
        try:
            with transaction.atomic():
                new_quantity = variant.quantity + quantity_change
                variant.quantity = new_quantity

                if purchase_price != variant.purchase_price:
                    variant.purchase_price = purchase_price

                if mrp != variant.mrp:
                    variant.mrp = mrp

                variant.save()

                inventory_log = InventoryLog.objects.create(
                    variant=variant,
                    supplier_invoice=supplier_invoice,
                    transaction_type=InventoryLog.TransactionTypes.STOCK_IN,
                    created_by=user,
                    quantity_change=quantity_change,
                    remaining_quantity=quantity_change,
                    new_quantity=variant.quantity,
                    total_value=quantity_change
                    * (purchase_price or variant.purchase_price),
                    purchase_price=purchase_price or variant.purchase_price,
                    mrp=mrp or variant.mrp,
                    notes=notes or f"Stock In: {quantity_change} units",
                )

                return inventory_log

        except Exception as e:
            print(e)
            return None

    @staticmethod
    def sale(variant, quantity_sold, user=None, invoice_item="", notes=""):
        """Process a sale and automatically update inventory"""
        with transaction.atomic():
            if quantity_sold <= 0:
                raise ValueError("Sale quantity must be positive")

            new_quantity = variant.quantity - quantity_sold
            variant.quantity = new_quantity
            variant.save()

            # Use selling price from invoice_item if available, otherwise variant's final_price
            unit_price = (invoice_item.unit_price if invoice_item else variant.final_price)
            
            # Perform FIFO allocation
            allocation_result = InventoryService._allocate_fifo(
                variant=variant,
                quantity_to_allocate=quantity_sold,
                invoice_item=invoice_item,
                unit_price=unit_price,
                user=user,
                notes=notes
            )

            return {
                "success": True,
                "quantity_sold": quantity_sold,
                "remaining_stock": new_quantity,
                "total_amount": quantity_sold * unit_price,
                "cogs": allocation_result["total_cogs"],
                "gross_profit": (quantity_sold * unit_price) - allocation_result["total_cogs"],
                "allocation_logs": allocation_result["logs"],
                "insufficient_stock_warning": allocation_result.get("insufficient_stock", False)
            }

    @staticmethod
    def _allocate_fifo(
        variant,
        quantity_to_allocate,
        invoice_item=None,
        unit_price=None,
        user=None,
        notes="",
    ):
        """Internal method to perform FIFO allocation"""
        remaining_to_allocate = Decimal(str(quantity_to_allocate))
        allocation_logs = []
        total_cogs = Decimal("0")
        insufficient_stock = False

        # Get available stock logs in FIFO order (oldest first)
        available_logs = InventoryLog.objects.filter(
            variant=variant,
            transaction_type__in=[
                InventoryLog.TransactionTypes.STOCK_IN,
                InventoryLog.TransactionTypes.INITIAL,
            ],
            remaining_quantity__gt=0,
        ).order_by("timestamp")

        # Allocate from available stock logs
        for stock_log in available_logs:
            if remaining_to_allocate <= 0:
                break

            # Calculate allocation from this log
            allocatable = min(stock_log.remaining_quantity, remaining_to_allocate)

            # Create sale log entry
            sale_log = InventoryLog.objects.create(
                variant=variant,
                transaction_type=InventoryLog.TransactionTypes.SALE,
                quantity_change=-allocatable,  # Negative for stock out
                new_quantity=variant.quantity,  # This will be the same for all allocations in this sale
                invoice_item=invoice_item,
                selling_price=unit_price,
                source_inventory_log=stock_log,
                allocated_quantity=allocatable,
                purchase_price=stock_log.purchase_price,
                total_value=allocatable * unit_price if unit_price else None,
                supplier_invoice = stock_log.supplier_invoice,
                created_by=user,
                notes=notes
                or f"FIFO Sale: {allocatable} from {stock_log.timestamp.date()}",
            )

            # Update remaining quantity in source log
            stock_log.remaining_quantity = F("remaining_quantity") - allocatable
            stock_log.save(update_fields=["remaining_quantity"])
            stock_log.refresh_from_db()

            # Track COGS
            if stock_log.purchase_price:
                total_cogs += allocatable * stock_log.purchase_price

            allocation_logs.append(sale_log)
            remaining_to_allocate -= allocatable

        # Handle insufficient stock (negative inventory)
        if remaining_to_allocate > 0:
            insufficient_stock = True
            # logger.warning(
            #     f"Insufficient stock for {variant}: {remaining_to_allocate} units short"
            # )

            # Create sale log for the unallocated quantity
            sale_log = InventoryLog.objects.create(
                variant=variant,
                transaction_type=InventoryLog.TransactionTypes.SALE,
                quantity_change=-remaining_to_allocate,
                new_quantity=variant.quantity,
                invoice_item=invoice_item,
                selling_price=unit_price,
                total_value=remaining_to_allocate * unit_price if unit_price else None,
                created_by=user,
                notes=(
                    f"INSUFFICIENT STOCK: {remaining_to_allocate} units - {notes}"
                    if notes
                    else f"INSUFFICIENT STOCK: {remaining_to_allocate} units"
                ),
            )
            allocation_logs.append(sale_log)

        return {
            "logs": allocation_logs,
            "total_cogs": total_cogs,
            "insufficient_stock": insufficient_stock,
        }

    @staticmethod
    def return_sale(variant, quantity_returned, user=None, notes="", invoice=None):
        """Process a customer return and restore inventory"""
        with transaction.atomic():
            if quantity_returned <= 0:
                raise ValueError("Return quantity must be positive")

            new_quantity = variant.quantity + quantity_returned
            variant.quantity = new_quantity
            variant.save()

            InventoryLog.objects.create(
                variant=variant,
                created_by=user,
                quantity_change=quantity_returned,  # Positive for returns
                new_quantity=new_quantity,
                transaction_type=InventoryLog.TransactionTypes.RETURN,
                notes=notes
                or f"Customer return: {quantity_returned} units{f' for {invoice.invoice_number}' if invoice else ''}",
            )

            return {
                "success": True,
                "quantity_returned": quantity_returned,
                "new_stock": new_quantity,
                "refund_amount": quantity_returned * variant.final_price,
            }

    @staticmethod
    def mark_as_damaged(
        variant, quantity_damaged, user=None, notes="", damage_type="General"
    ):
        """Mark items as damaged and move them to damaged inventory"""
        with transaction.atomic():
            if quantity_damaged <= 0:
                raise ValueError("Damaged quantity must be positive")

            # Move from available to damaged
            variant.quantity -= quantity_damaged
            variant.damaged_quantity += quantity_damaged
            variant.save()

            # Create inventory log
            InventoryLog.objects.create(
                variant=variant,
                created_by=user,
                quantity_change=-quantity_damaged,  # Negative for available stock
                new_quantity=variant.quantity,
                total_value=quantity_damaged * variant.purchase_price,
                transaction_type=InventoryLog.TransactionTypes.DAMAGE,
                notes=notes
                or f"Marked as damaged: {quantity_damaged} units - {damage_type}. {notes}",
            )

            return {
                "success": True,
                "quantity_damaged": quantity_damaged,
                "remaining_available": variant.quantity,
                "total_damaged": variant.damaged_quantity,
                "damage_type": damage_type,
            }

    @staticmethod
    def repair_damaged(variant, quantity_repaired, user=None, notes=""):
        """Repair damaged items and move them back to available inventory"""
        with transaction.atomic():
            if quantity_repaired <= 0:
                raise ValueError("Repair quantity must be positive")

            if variant.damaged_quantity < quantity_repaired:
                raise ValueError(
                    f"Insufficient damaged stock to repair. Damaged: {variant.damaged_quantity}, Requested: {quantity_repaired}"
                )

            # Move from damaged to available
            variant.damaged_quantity -= quantity_repaired
            variant.quantity += quantity_repaired
            variant.save()

            # Create inventory log
            InventoryLog.objects.create(
                variant=variant,
                created_by=user,
                quantity_change=quantity_repaired,  # Positive for available stock
                new_quantity=variant.quantity,
                transaction_type=InventoryLog.TransactionTypes.ADJUSTMENT_IN,
                notes=f"Repaired damaged items: {quantity_repaired} units. {notes}",
            )

            return {
                "success": True,
                "quantity_repaired": quantity_repaired,
                "new_available": variant.quantity,
                "remaining_damaged": variant.damaged_quantity,
            }

    @staticmethod
    def dispose_damaged(
        variant, quantity_disposed, user=None, notes="", disposal_reason="Damaged"
    ):
        """Dispose of damaged items (permanently remove from inventory)"""
        with transaction.atomic():
            if quantity_disposed <= 0:
                raise ValueError("Disposal quantity must be positive")

            if variant.damaged_quantity < quantity_disposed:
                raise ValueError(
                    f"Insufficient damaged stock to dispose. Damaged: {variant.damaged_quantity}, Requested: {quantity_disposed}"
                )

            # Remove from damaged inventory
            variant.damaged_quantity -= quantity_disposed
            variant.save()

            # Create inventory log
            InventoryLog.objects.create(
                variant=variant,
                created_by=user,
                quantity_change=0,  # No change to available stock
                new_quantity=variant.quantity,
                transaction_type=InventoryLog.TransactionTypes.ADJUSTMENT_OUT,
                notes=f"Disposed damaged items: {quantity_disposed} units - {disposal_reason}. {notes}",
            )

            return {
                "success": True,
                "quantity_disposed": quantity_disposed,
                "remaining_damaged": variant.damaged_quantity,
                "disposal_reason": disposal_reason,
            }
