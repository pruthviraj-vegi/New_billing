/**
 * Searchable Select Functionality
 * Converts a select dropdown to a searchable input using existing options
 */

class SearchableSelect {
    constructor() {
        this.searchInput = document.getElementById('referred_by_search');
        this.selectElement = document.querySelector('select[name="referred_by"]');
        this.dropdown = document.getElementById('select_dropdown');
        this.clearBtn = document.getElementById('clear_referred_by');
        this.originalOptions = [];
        this.filteredOptions = [];
        this.selectedIndex = -1;
        
        if (!this.searchInput || !this.selectElement || !this.dropdown) {
            console.warn('Searchable select elements not found');
            return;
        }
        
        this.init();
    }
    
    init() {
        this.extractOptions();
        this.bindEvents();
        this.loadInitialValue();
    }
    
    extractOptions() {
        // Extract all options from the select element
        this.originalOptions = Array.from(this.selectElement.options).map(option => ({
            value: option.value,
            text: option.textContent,
            element: option
        }));
        this.filteredOptions = [...this.originalOptions];
    }
    
    bindEvents() {
        // Search input events
        this.searchInput.addEventListener('input', (e) => this.handleInput(e));
        this.searchInput.addEventListener('keydown', (e) => this.handleKeydown(e));
        this.searchInput.addEventListener('focus', () => this.handleFocus());
        this.searchInput.addEventListener('blur', (e) => this.handleBlur(e));
        
        // Clear button
        this.clearBtn.addEventListener('click', () => this.clearSelection());
        
        // Click outside to close
        document.addEventListener('click', (e) => this.handleClickOutside(e));
        
        // Select change event
        this.selectElement.addEventListener('change', () => this.handleSelectChange());
    }
    
    loadInitialValue() {
        // Load the current selected value
        if (this.selectElement.value) {
            const selectedOption = this.originalOptions.find(opt => opt.value === this.selectElement.value);
            if (selectedOption) {
                this.searchInput.value = selectedOption.text;
                this.clearBtn.style.display = 'block';
            }
        }
    }
    
    handleInput(e) {
        const query = e.target.value.toLowerCase().trim();
        
        // Show clear button if there's text
        this.clearBtn.style.display = query ? 'block' : 'none';
        
        // Filter options based on search query
        this.filteredOptions = this.originalOptions.filter(option => 
            option.text.toLowerCase().includes(query)
        );
        
        // Update dropdown display
        this.updateDropdown();
        
        // Show/hide dropdown
        if (query.length > 0) {
            this.showDropdown();
        } else {
            this.hideDropdown();
        }
        
        // Reset selection
        this.selectedIndex = -1;
    }
    
    handleKeydown(e) {
        if (!this.dropdown.classList.contains('show')) {
            return;
        }
        
        const visibleOptions = this.getVisibleOptions();
        
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.selectedIndex = Math.min(this.selectedIndex + 1, visibleOptions.length - 1);
                this.updateSelection(visibleOptions);
                break;
                
            case 'ArrowUp':
                e.preventDefault();
                this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
                this.updateSelection(visibleOptions);
                break;
                
            case 'Enter':
                e.preventDefault();
                if (this.selectedIndex >= 0 && visibleOptions[this.selectedIndex]) {
                    this.selectOption(visibleOptions[this.selectedIndex]);
                }
                break;
                
            case 'Escape':
                this.hideDropdown();
                this.searchInput.blur();
                break;
        }
    }
    
    handleFocus() {
        if (this.searchInput.value.length > 0) {
            this.showDropdown();
        }
    }
    
    handleBlur(e) {
        // Delay hiding to allow for clicks on options
        setTimeout(() => {
            if (!this.dropdown.contains(document.activeElement)) {
                this.hideDropdown();
            }
        }, 150);
    }
    
    handleClickOutside(e) {
        if (!this.searchInput.contains(e.target) && !this.dropdown.contains(e.target)) {
            this.hideDropdown();
        }
    }
    
    handleSelectChange() {
        // Update search input when select changes
        if (this.selectElement.value) {
            const selectedOption = this.originalOptions.find(opt => opt.value === this.selectElement.value);
            if (selectedOption) {
                this.searchInput.value = selectedOption.text;
                this.clearBtn.style.display = 'block';
            }
        } else {
            this.searchInput.value = '';
            this.clearBtn.style.display = 'none';
        }
    }
    
    updateDropdown() {
        // Clear existing options
        this.selectElement.innerHTML = '';
        
        // Add filtered options
        this.filteredOptions.forEach(option => {
            const optionElement = document.createElement('option');
            optionElement.value = option.value;
            optionElement.textContent = option.text;
            this.selectElement.appendChild(optionElement);
        });
    }
    
    getVisibleOptions() {
        return Array.from(this.selectElement.options);
    }
    
    updateSelection(options) {
        options.forEach((option, index) => {
            option.style.backgroundColor = index === this.selectedIndex ? 'var(--primary)' : '';
            option.style.color = index === this.selectedIndex ? 'var(--text-on-primary)' : '';
        });
    }
    
    selectOption(option) {
        this.selectElement.value = option.value;
        this.searchInput.value = option.textContent;
        this.clearBtn.style.display = 'block';
        this.hideDropdown();
        
        // Trigger change event
        this.selectElement.dispatchEvent(new Event('change', { bubbles: true }));
    }
    
    showDropdown() {
        this.dropdown.classList.add('show');
    }
    
    hideDropdown() {
        this.dropdown.classList.remove('show');
        this.selectedIndex = -1;
    }
    
    clearSelection() {
        this.selectElement.value = '';
        this.searchInput.value = '';
        this.clearBtn.style.display = 'none';
        this.hideDropdown();
        
        // Trigger change event
        this.selectElement.dispatchEvent(new Event('change', { bubbles: true }));
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    new SearchableSelect();
});
