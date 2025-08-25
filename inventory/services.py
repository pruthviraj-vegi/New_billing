from django.db import transaction
from .models import InventoryLog


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
    def sale(variant, quantity_sold, user=None, notes="", invoice=None):
        """Process a sale and automatically update inventory"""
        with transaction.atomic():
            if quantity_sold <= 0:
                raise ValueError("Sale quantity must be positive")

            new_quantity = variant.quantity - quantity_sold
            variant.quantity = new_quantity
            variant.save()

            InventoryLog.objects.create(
                variant=variant,
                created_by=user,
                quantity_change=-quantity_sold,  # Negative for sales
                new_quantity=new_quantity,
                transaction_type=InventoryLog.TransactionTypes.SALE,
                total_value=quantity_sold * variant.final_price,
                notes=notes
                or f"Sale: {quantity_sold} units{f' for {invoice.invoice_number}' if invoice else ''}",
            )

            return {
                "success": True,
                "quantity_sold": quantity_sold,
                "remaining_stock": new_quantity,
                "total_amount": quantity_sold * variant.final_price,
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

    # Bulk Operations
    @classmethod
    def bulk_sale(cls, items, user=None, invoice=None):
        """Process multiple items in a single transaction"""
        with transaction.atomic():
            results = []
            total_amount = 0
            total_items = 0
            errors = []

            for item in items:
                try:
                    variant = item["variant"]
                    quantity = item["quantity"]
                    notes = item.get("notes", "")

                    # Process individual sale
                    result = cls.sale(variant, quantity, user, notes, invoice)
                    results.append(result)

                    total_amount += result["total_amount"]
                    total_items += quantity

                except Exception as e:
                    errors.append(
                        {"variant": variant, "error": str(e), "quantity": quantity}
                    )

            return {
                "success": len(errors) == 0,
                "total_items_sold": total_items,
                "total_amount": total_amount,
                "individual_results": results,
                "errors": errors,
                "summary": {
                    "successful_sales": len(results),
                    "failed_sales": len(errors),
                    "total_revenue": total_amount,
                },
            }

    @classmethod
    def bulk_return(cls, items, user=None, invoice=None):
        """Process multiple returns in a single transaction"""
        with transaction.atomic():
            results = []
            total_refund = 0
            total_items = 0
            errors = []

            for item in items:
                try:
                    variant = item["variant"]
                    quantity = item["quantity"]
                    notes = item.get("notes", "")

                    # Process individual return
                    result = cls.return_sale(variant, quantity, user, notes, invoice)
                    results.append(result)

                    total_refund += result["refund_amount"]
                    total_items += quantity

                except Exception as e:
                    errors.append(
                        {"variant": variant, "error": str(e), "quantity": quantity}
                    )

            return {
                "success": len(errors) == 0,
                "total_items_returned": total_items,
                "total_refund": total_refund,
                "individual_results": results,
                "errors": errors,
                "summary": {
                    "successful_returns": len(results),
                    "failed_returns": len(errors),
                    "total_refund_amount": total_refund,
                },
            }

    @classmethod
    def bulk_update_quantity(cls, updates, user=None):
        """Bulk update quantities for multiple variants"""
        with transaction.atomic():
            results = []
            errors = []

            for update in updates:
                try:
                    variant = update["variant"]
                    change = update["change"]
                    notes = update.get("notes", "")

                    # Process individual update
                    cls.update_quantity(variant, change, user, notes)
                    results.append(
                        {
                            "variant": variant,
                            "change": change,
                            "new_quantity": variant.quantity,
                        }
                    )

                except Exception as e:
                    errors.append(
                        {"variant": variant, "error": str(e), "change": change}
                    )

            return {
                "success": len(errors) == 0,
                "successful_updates": len(results),
                "failed_updates": len(errors),
                "results": results,
                "errors": errors,
            }

    @classmethod
    def bulk_mark_damaged(cls, items, user=None):
        """Bulk mark multiple items as damaged"""
        with transaction.atomic():
            results = []
            errors = []

            for item in items:
                try:
                    variant = item["variant"]
                    quantity = item["quantity"]
                    damage_type = item.get("damage_type", "General")
                    notes = item.get("notes", "")

                    result = cls.mark_as_damaged(
                        variant, quantity, user, notes, damage_type
                    )
                    results.append(result)

                except Exception as e:
                    errors.append(
                        {"variant": variant, "error": str(e), "quantity": quantity}
                    )

            return {
                "success": len(errors) == 0,
                "successful_damages": len(results),
                "failed_damages": len(errors),
                "results": results,
                "errors": errors,
            }
