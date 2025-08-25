/**
 * Cart Management JavaScript
 * Handles all cart operations including add, update, delete, and barcode scanning
 */

class CartManager {
    constructor() {
        this.initializeElements();
        this.attachEventListeners();
        this.setupCurrencyFormatter();
        this.setupNotificationFallback();
        this.focusBarcodeInput();
    }

    initializeElements() {
        // Get data from global variables set by Django template
        if (!window.CART_DATA) {
            console.error('CART_DATA not found. Make sure the template is properly loaded.');
            return;
        }
        
        this.csrfToken = window.CART_DATA.csrfToken;
        this.cartId = window.CART_DATA.cartId;
        this.urls = window.CART_DATA.urls;
        
        // DOM elements
        this.barcodeForm = document.getElementById('barcodeForm');
        this.barcodeInput = document.getElementById('barcodeInput');
        this.cartItemsBody = document.getElementById('cartItemsBody');
        this.totalItems = document.getElementById('totalItems');
        this.totalAmount = document.getElementById('totalAmount');
        
        if (!this.csrfToken || !this.cartId) {
            console.error('Required data not found. CSRF Token:', !!this.csrfToken, 'Cart ID:', this.cartId);
            return;
        }
    }

    attachEventListeners() {
        // Event delegation for table actions
        if (this.cartItemsBody) {
            this.cartItemsBody.addEventListener('click', this.handleTableActions.bind(this));
            this.cartItemsBody.addEventListener('keydown', this.handleInputKeydown.bind(this));
        }

        // Barcode form submission
        if (this.barcodeForm) {
            this.barcodeForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const barcode = this.barcodeInput.value.trim();
                if (!barcode) {
                    this.showNotification('Please enter a barcode', 'error');
                    return;
                }
                this.handleBarcodeSubmit(this.cartId, barcode);
            });
        }

        // Cart options dropdown event listeners
        this.attachDropdownEventListeners();

        // Real-time discount calculation
        this.attachRealTimeDiscountCalculation();
    }

    // Add real-time discount calculation
    attachRealTimeDiscountCalculation() {
        if (this.cartItemsBody) {
            this.cartItemsBody.addEventListener('input', (e) => {
                const target = e.target;
                if (target.classList.contains('quantity-input') || target.classList.contains('price-input')) {
                    this.updateDiscountInRealTime(target);
                }
            });
        }
    }

    updateDiscountInRealTime(input) {
        const row = input.closest('tr');
        if (!row) return;

        const quantityInput = row.querySelector('.quantity-input');
        const priceInput = row.querySelector('.price-input');
        const discountCell = row.querySelector('.discount-cell'); // Use the class selector
        const amountCell = row.querySelector('.amount-cell');

        if (!quantityInput || !priceInput || !discountCell || !amountCell) return;

        const quantity = parseFloat(quantityInput.value) || 0;
        const price = parseFloat(priceInput.value) || 0;
        const sellingPrice = parseFloat(row.querySelector('td:nth-child(4)').textContent.replace(/[^\d.-]/g, '')) || 0;

        // Calculate new amount
        const newAmount = (quantity * price).toFixed(2);
        amountCell.textContent = this.formatCurrency(newAmount);

        // Calculate new discount
        if (sellingPrice > 0) {
            const discount = Math.max(0, ((sellingPrice - price) / sellingPrice) * 100);
            discountCell.textContent = `${discount.toFixed(2)}%`;
        } else {
            discountCell.textContent = '0%';
        }
    }

    attachDropdownEventListeners() {
        // Initialize dropdown functionality
        this.initializeDropdown();

        // Archive cart button
        const archiveCartBtn = document.getElementById('archiveCartBtn');
        if (archiveCartBtn) {
            archiveCartBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.showConfirmModal(
                    'Archive Cart',
                    'Are you sure you want to archive this cart? This action cannot be undone.',
                    () => this.archiveCart()
                );
            });
        }

        // Clear cart button
        const clearCartBtn = document.getElementById('clearCartBtn');
        if (clearCartBtn) {
            clearCartBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.showConfirmModal(
                    'Clear Cart',
                    'Are you sure you want to clear all items from this cart? This action cannot be undone.',
                    () => this.clearCart()
                );
            });
        }

        // Print cart button
        const printCartBtn = document.getElementById('printCartBtn');
        if (printCartBtn) {
            printCartBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.printCart();
            });
        }

        // Export cart button
        const exportCartBtn = document.getElementById('exportCartBtn');
        if (exportCartBtn) {
            exportCartBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.exportCart();
            });
        }
    }

    initializeDropdown() {
        const dropdownToggle = document.getElementById('cartOptionsDropdown');
        const dropdownMenu = document.querySelector('.cart-dropdown .dropdown-menu');
        
        if (dropdownToggle && dropdownMenu) {
            // Try Bootstrap first
            if (typeof bootstrap !== 'undefined') {
                const dropdown = new bootstrap.Dropdown(dropdownToggle);
                return;
            }
            
            // Fallback: manual dropdown toggle
            dropdownToggle.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                const isOpen = dropdownMenu.classList.contains('show');
                
                // Close all other dropdowns
                document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
                    menu.classList.remove('show');
                });
                
                // Toggle current dropdown
                if (!isOpen) {
                    dropdownMenu.classList.add('show');
                }
            });
            
            // Close dropdown when clicking outside
            document.addEventListener('click', (e) => {
                if (!dropdownToggle.contains(e.target) && !dropdownMenu.contains(e.target)) {
                    dropdownMenu.classList.remove('show');
                }
            });
            
            // Close dropdown when pressing Escape
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    dropdownMenu.classList.remove('show');
                }
            });
        }
    }

    setupCurrencyFormatter() {
        this.currencyFormatter = new Intl.NumberFormat('en-IN', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    setupNotificationFallback() {
        if (typeof showNotification === 'undefined') {
            window.showNotification = this.createToastNotification.bind(this);
        }
    }

    focusBarcodeInput() {
        if (this.barcodeInput) {
            this.barcodeInput.focus();
        }
    }

    // Event Handlers
    handleInputKeydown(e) {
        if (e.key !== 'Enter') 
            return;
        


        const target = e.target;
        if (! target.classList.contains('quantity-input') && ! target.classList.contains('price-input')) {
            return;
        }

        e.preventDefault();

        const itemId = target.dataset.itemId;
        if (itemId) {
            this.handleUpdateItem(itemId);
        }
    }

    handleTableActions(e) {
        const target = e.target;
        const button = target.closest('.update-item-btn, .delete-item-btn');

        if (! button) 
            return;
        


        const itemId = button.dataset.itemId;
        if (! itemId) 
            return;
        


        if (button.classList.contains('update-item-btn')) {
            this.handleUpdateItem(itemId);
        } else if (button.classList.contains('delete-item-btn')) {
            this.handleDeleteItem(itemId);
        }
    }

    // Item Management
    handleUpdateItem(itemId) {
        const row = document.getElementById(`cart-item-${itemId}`);
        if (!row) {
            this.showNotification('Item not found', 'error');
            return;
        }

        const quantityInput = row.querySelector('.quantity-input');
        const priceInput = row.querySelector('.price-input');
        const amountCell = row.querySelector('.amount-cell');
        const discountCell = row.querySelector('.discount-cell');

        if (!quantityInput || !priceInput || !amountCell) {
            this.showNotification('Invalid form inputs', 'error');
            return;
        }

        // Store original values for rollback
        const originalValues = {
            quantity: quantityInput.value,
            price: priceInput.value,
            amount: amountCell.textContent,
            discount: discountCell ? discountCell.textContent : '0%',
            totalAmount: this.totalAmount.textContent
        };

        const quantity = parseFloat(quantityInput.value);
        const price = parseFloat(priceInput.value);

        if (!quantity || !price || quantity <= 0 || price < 0) {
            this.showNotification('Please enter valid quantity and price', 'error');
            return;
        }

        this.updateCartItem(itemId, quantity, price, originalValues);
    }

    handleDeleteItem(itemId) {
        if (!confirm('Are you sure you want to remove this item?')) 
            return;
        

        this.deleteCartItem(itemId);
    }

    // API Operations
    async updateCartItem(itemId, quantity, price, originalValues) {
        const row = document.getElementById(`cart-item-${itemId}`);
        const quantityInput = row?.querySelector('.quantity-input');
        const priceInput = row?.querySelector('.price-input');
        const amountCell = row?.querySelector('.amount-cell');
        const discountCell = row?.querySelector('.discount-cell');
        
        // Show loading state
        const updateButton = row?.querySelector(`.update-item-btn[data-item-id="${itemId}"]`);
        if (updateButton) {
            updateButton.disabled = true;
            updateButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        }
        
        try {
            // Optimistic UI update
            const newAmount = (quantity * price).toFixed(2);
            if (quantityInput) quantityInput.value = quantity;
            if (priceInput) priceInput.value = price;
            if (amountCell) amountCell.textContent = this.formatCurrency(newAmount);
            
            // Calculate and update discount optimistically
            if (discountCell) {
                const sellingPrice = parseFloat(row.querySelector('td:nth-child(4)').textContent.replace(/[^\d.-]/g, ''));
                if (sellingPrice > 0) {
                    const discount = Math.max(0, ((sellingPrice - price) / sellingPrice) * 100);
                    discountCell.textContent = `${discount.toFixed(2)}%`;
                }
            }
            
            // Use the cart ID from the data attribute
            const response = await fetch(this.urls.manageItem.replace('0', itemId), {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({ quantity, price })
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.showNotification('Item updated successfully', 'success');
                
                // Update with server response data
                if (data.cart_item) {
                    if (amountCell) amountCell.textContent = this.formatCurrency(data.cart_item.amount);
                    
                    // Update discount percentage if available
                    if (data.cart_item.discount_percentage !== undefined && discountCell) {
                        discountCell.textContent = `${data.cart_item.discount_percentage}%`;
                    }
                }
                
                this.updateTotalAmount(data.cart_total);
            } else {
                this.rollbackItemUpdate(itemId, originalValues);
                this.showNotification(data.message || 'Update failed - values restored', 'error');
            }
        } catch (error) {
            console.error('Error updating item:', error);
            this.rollbackItemUpdate(itemId, originalValues);
            this.showNotification('Network error - values restored', 'error');
        } finally {
            if (updateButton) {
                updateButton.disabled = false;
                updateButton.innerHTML = '<i class="fas fa-save"></i>';
                this.barcodeInput.focus();
            }
        }
    }

    async deleteCartItem(itemId) {
        const row = document.getElementById(`cart-item-${itemId}`);
        if (! row) {
            this.showNotification('Item not found', 'error');
            return;
        }

        const originalRowHTML = row.outerHTML;
        const originalTotalItems = this.totalItems.textContent;
        const originalTotalAmount = this.totalAmount.textContent;

        // Show loading state
        const deleteButton = row.querySelector(`.delete-item-btn[data-item-id="${itemId}"]`);
        if (deleteButton) {
            deleteButton.disabled = true;
            deleteButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        }

        try { // Optimistic removal
            row.style.opacity = '0.5';

            const response = await fetch(this.urls.manageItem.replace('0', itemId), {
                method: 'DELETE',
                headers: { 'X-CSRFToken': this.csrfToken }
            });

            const data = await response.json();

            if (data.status === 'success') {
                this.showNotification('Item removed successfully', 'success');
                row.remove();
                this.updateTotalAmount(data.cart_total);
                this.updateTotalItems(-1);
            } else { // Rollback
                row.style.opacity = '1';
                if (deleteButton) {
                    deleteButton.disabled = false;
                    deleteButton.innerHTML = '<i class="fas fa-trash"></i>';
                }
                this.showNotification(data.message || 'Delete failed', 'error');
            }
        } catch (error) {
            console.error('Error deleting item:', error);

            // Rollback
            row.style.opacity = '1';
            if (deleteButton) {
                deleteButton.disabled = false;
                deleteButton.innerHTML = '<i class="fas fa-trash"></i>';
            }
            this.showNotification('Network error - item not removed', 'error');
        } finally {
            this.barcodeInput.focus();
        }
    }

    async handleBarcodeSubmit(cartId, barcode) {
        const originalTotalItems = this.totalItems.textContent;
        const originalTotalAmount = this.totalAmount.textContent;
        
        try {
            const requestBody = { barcode, cart_id: parseInt(cartId), quantity: 1 };
            
            const response = await fetch(this.urls.scanBarcode, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify(requestBody)
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('Response error:', errorText);
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.barcodeInput.value = '';
                
                if (!data.cart_item) {
                    this.showNotification('Invalid response structure', 'error');
                    return;
                }

                if (data.type === 'Create') {
                    const newItem = this.createCartItem(data.cart_item);
                    // Add new items at the top
                    if (this.cartItemsBody.firstChild) {
                        this.cartItemsBody.insertBefore(newItem, this.cartItemsBody.firstChild);
                    } else {
                        this.cartItemsBody.appendChild(newItem);
                    }
                    this.updateTotalItems(1);
                    this.showNotification('Item added successfully', 'success');
                } else if (data.type === 'Update') {
                    this.updateExistingCartItem(data.cart_item);
                    this.showNotification('Item updated successfully', 'success');
                }
                
                if (data.cart_total !== undefined) {
                    this.updateTotalAmount(data.cart_total);
                }
            } else {
                this.showNotification(data.message, 'error');
            }
        } catch (error) {
            console.error('Error in barcode submission:', error);
            this.showNotification(`Error adding product to cart: ${error.message}`, 'error');
        } finally {
            this.barcodeInput.focus();
        }
    }

    // Helper Functions
    rollbackItemUpdate(itemId, originalValues) {
        const row = document.getElementById(`cart-item-${itemId}`);
        if (!row || !originalValues) 
            return;
        

        const quantityInput = row.querySelector('.quantity-input');
        const priceInput = row.querySelector('.price-input');
        const amountCell = row.querySelector('.amount-cell');
        const discountCell = row.querySelector('.discount-cell');

        if (quantityInput && originalValues.quantity) {
            quantityInput.value = originalValues.quantity;
        }
        if (priceInput && originalValues.price) {
            priceInput.value = originalValues.price;
        }
        if (amountCell && originalValues.amount) {
            amountCell.textContent = originalValues.amount;
        }
        if (discountCell && originalValues.discount) {
            discountCell.textContent = originalValues.discount;
        }

        if (originalValues.totalAmount) {
            this.totalAmount.textContent = originalValues.totalAmount;
        }

        console.log('Rolled back item values for item:', itemId);
    }

    updateExistingCartItem(cartItem) {
        const existingRow = document.getElementById(`cart-item-${cartItem.id}`);

        if (existingRow) {
            const quantityInput = existingRow.querySelector('.quantity-input');
            const amountCell = existingRow.querySelector('.amount-cell');
            const discountCell = existingRow.querySelector('.discount-cell');

            if (quantityInput) quantityInput.value = cartItem.quantity;
            if (amountCell) amountCell.textContent = this.formatCurrency(cartItem.amount);
            
            // Update discount percentage - calculate if not provided
            if (discountCell) {
                if (cartItem.discount_percentage !== undefined) {
                    discountCell.textContent = `${cartItem.discount_percentage}%`;
                } else {
                    // Calculate discount from selling price and current price
                    const sellingPrice = parseFloat(existingRow.querySelector('td:nth-child(4)').textContent.replace(/[^\d.-]/g, '')) || 0;
                    const currentPrice = parseFloat(cartItem.price) || 0;
                    if (sellingPrice > 0) {
                        const discount = Math.max(0, ((sellingPrice - currentPrice) / sellingPrice) * 100);
                        discountCell.textContent = `${discount.toFixed(2)}%`;
                    }
                }
            }
        } else {
            // Fallback: create new item if row not found
            const newItem = this.createCartItem(cartItem);
            if (this.cartItemsBody.firstChild) {
                this.cartItemsBody.insertBefore(newItem, this.cartItemsBody.firstChild);
            } else {
                this.cartItemsBody.appendChild(newItem);
            }
            this.updateTotalItems(1);
        }
    }

    createCartItem(data) {
        const item = document.createElement('tr');
        item.id = `cart-item-${
            data.id
        }`;

        const {
            product_variant: {
                barcode = 'N/A',
                brand = 'N/A',
                simple_name: variantName = 'N/A',
                mrp: sellingPrice = data.price || '0.00',
                discount_percentage: discount = 0
            } = {}
        } = data;

        // Calculate discount if not provided
        let calculatedDiscount = discount;
        if (sellingPrice > 0 && data.price) {
            calculatedDiscount = Math.max(0, ((sellingPrice - data.price) / sellingPrice) * 100);
        }

        item.innerHTML = `
            <td>${barcode}</td>
            <td>${brand}</td>
            <td>${variantName}</td>
            <td>${
            this.formatCurrency(sellingPrice)
        }</td>
            <td>
                <input type="number" class="form-input quantity-input" value="${
            data.quantity
        }" 
                       data-item-id="${
            data.id
        }" min="0.01" step="0.01" 
                       title="Press Enter to update">
            </td>
            <td>
                <input type="number" class="form-input price-input" value="${
            data.price
        }" 
                       data-item-id="${
            data.id
        }" min="0" step="0.01" 
                       title="Press Enter to update">
            </td>
            <td class="discount-cell">${calculatedDiscount.toFixed(2)}%</td>
            <td class="amount-cell">${
            this.formatCurrency(data.amount)
        }</td>
            <td>
                <button type="button" class="btn btn-primary update-item-btn" data-item-id="${
            data.id
        }" 
                        title="Save changes">
                    <i class="fas fa-save"></i>
                </button>
                <button type="button" class="btn btn-danger delete-item-btn" data-item-id="${
            data.id
        }" 
                        title="Remove item">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        `;

        return item;
    }

    updateRowAmount(itemId, quantity, price) {
        const row = document.getElementById(`cart-item-${itemId}`);
        if (row) {
            const amount = (quantity * price).toFixed(2);
            const amountCell = row.querySelector('.amount-cell');
            if (amountCell) {
                amountCell.textContent = this.formatCurrency(amount);
            }
        }
    }

    removeCartRow(itemId) {
        const row = document.getElementById(`cart-item-${itemId}`);
        if (row) {
            row.remove();
        }
    }

    updateTotalAmount(newTotal) {
        this.totalAmount.textContent = this.formatCurrency(newTotal);
    }

    updateTotalItems(change) {
        const current = parseInt(this.totalItems.textContent) || 0;
        this.totalItems.textContent = current + change;
    }

    formatCurrency(amount) {
        return this.currencyFormatter.format(amount);
    }

    createToastNotification(message, type) {
        console.log(`${
            type.toUpperCase()
        }: ${message}`);

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed; top: 20px; right: 20px; z-index: 9999;
            padding: 10px 20px; border-radius: 4px; color: white;
            background: ${
            type === 'success' ? '#28a745' : '#dc3545'
        };
            font-weight: bold; box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        `;

        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    showNotification(message, type) {
        if (typeof window.showNotification !== 'undefined') {
            window.showNotification(message, type);
        } else {
            this.createToastNotification(message, type);
        }
    }

    // Cart Options Methods
    showConfirmModal(title, message, onConfirm) {
        const modal = document.getElementById('confirmModal');
        const modalTitle = document.getElementById('confirmModalLabel');
        const modalBody = document.getElementById('confirmModalBody');
        const confirmBtn = document.getElementById('confirmActionBtn');

        if (modal && modalTitle && modalBody && confirmBtn) {
            modalTitle.textContent = title;
            modalBody.textContent = message;
            
            // Remove existing event listeners
            const newConfirmBtn = confirmBtn.cloneNode(true);
            confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
            
            // Add new event listener
            newConfirmBtn.addEventListener('click', () => {
                onConfirm();
                this.hideModal(modal);
            });

            // Show modal
            const bootstrapModal = new bootstrap.Modal(modal);
            bootstrapModal.show();
        }
    }

    hideModal(modal) {
        const bootstrapModal = bootstrap.Modal.getInstance(modal);
        if (bootstrapModal) {
            bootstrapModal.hide();
        }
    }

    async archiveCart() {
        try {
            const response = await fetch(this.urls.archiveCart, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'Content-Type': 'application/json',
                },
            });

            const data = await response.json();
            
            if (data.status === 'success') {
                this.showNotification('Cart archived successfully', 'success');
                // Redirect to main cart page after a short delay
                setTimeout(() => {
                    window.location.href = '/cart/';
                }, 1500);
            } else {
                this.showNotification(data.message || 'Failed to archive cart', 'error');
            }
        } catch (error) {
            console.error('Error archiving cart:', error);
            this.showNotification('Failed to archive cart', 'error');
        }
    }

    async clearCart() {
        try {
            const response = await fetch(this.urls.clearCart, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'Content-Type': 'application/json',
                },
            });

            const data = await response.json();
            
            if (data.status === 'success') {
                this.showNotification('Cart cleared successfully', 'success');
                // Clear the table body
                if (this.cartItemsBody) {
                    this.cartItemsBody.innerHTML = '';
                }
                // Update totals
                this.updateTotalAmount(0);
                this.updateTotalItems(-parseInt(this.totalItems.textContent || 0));
            } else {
                this.showNotification(data.message || 'Failed to clear cart', 'error');
            }
        } catch (error) {
            console.error('Error clearing cart:', error);
            this.showNotification('Failed to clear cart', 'error');
        }
    }

    printCart() {
        // Create a print-friendly version of the cart
        const printWindow = window.open('', '_blank');
        const cartData = this.getCartDataForPrint();
        
        printWindow.document.write(`
            <html>
                <head>
                    <title>Cart - ${this.cartId}</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 20px; }
                        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                        th { background-color: #f2f2f2; }
                        .total { font-weight: bold; font-size: 1.2em; }
                    </style>
                </head>
                <body>
                    <h1>Cart Details</h1>
                    <p><strong>Cart ID:</strong> ${this.cartId}</p>
                    <p><strong>Date:</strong> ${new Date().toLocaleDateString()}</p>
                    ${cartData}
                    <div class="total">
                        <p><strong>Total Items:</strong> ${this.totalItems.textContent}</p>
                        <p><strong>Total Amount:</strong> ${this.totalAmount.textContent}</p>
                    </div>
                </body>
            </html>
        `);
        
        printWindow.document.close();
        printWindow.print();
    }

    exportCart() {
        // Export cart data as CSV
        const cartData = this.getCartDataForExport();
        const csvContent = this.convertToCSV(cartData);
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        
        if (link.download !== undefined) {
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', `cart_${this.cartId}_${new Date().toISOString().split('T')[0]}.csv`);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    }

    getCartDataForPrint() {
        const rows = this.cartItemsBody.querySelectorAll('tr');
        let html = '<table><thead><tr><th>Barcode</th><th>Product</th><th>Variant</th><th>Quantity</th><th>Price</th><th>Amount</th></tr></thead><tbody>';
        
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            if (cells.length >= 8) {
                html += `<tr>
                    <td>${cells[0].textContent}</td>
                    <td>${cells[1].textContent}</td>
                    <td>${cells[2].textContent}</td>
                    <td>${cells[4].querySelector('input')?.value || cells[4].textContent}</td>
                    <td>${cells[5].querySelector('input')?.value || cells[5].textContent}</td>
                    <td>${cells[7].textContent}</td>
                </tr>`;
            }
        });
        
        html += '</tbody></table>';
        return html;
    }

    getCartDataForExport() {
        const rows = this.cartItemsBody.querySelectorAll('tr');
        const data = [];
        
        // Add header
        data.push(['Barcode', 'Product', 'Variant', 'Quantity', 'Price', 'Amount']);
        
        // Add data rows
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            if (cells.length >= 8) {
                data.push([
                    cells[0].textContent,
                    cells[1].textContent,
                    cells[2].textContent,
                    cells[4].querySelector('input')?.value || cells[4].textContent,
                    cells[5].querySelector('input')?.value || cells[5].textContent,
                    cells[7].textContent
                ]);
            }
        });
        
        return data;
    }

    convertToCSV(data) {
        return data.map(row => 
            row.map(cell => `"${cell}"`).join(',')
        ).join('\n');
    }
}

// Initialize cart manager when DOM is ready
document.addEventListener('DOMContentLoaded', function () {
    window.cartManager = new CartManager();
});
