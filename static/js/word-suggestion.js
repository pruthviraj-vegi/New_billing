/**
 * Optimized Word Suggestion System for Spelling Correction
 * 
 * Improvements:
 * - Consistent debounce delay from options (no hardcoding)
 * - AbortController to cancel stale requests
 * - ARIA roles for accessibility
 * - Optimized keyboard navigation
 * - Event-driven integration (no reliance on window.loadTableData)
 * - Cleaner dropdown visibility handling (CSS classes only)
 */

class WordSuggestion {
    constructor(inputElement, options = {}) {
        this.input = inputElement;
        this.options = {
            debounceDelay: 300,
            minQueryLength: 2,
            maxSuggestions: 5,
            url: options.fetchUrl || (window.urls && window.urls.suggestions) || "",
            placeholder: 'Type to get word suggestions...',
            onSuggestionSelected: null, // optional callback
            ...options
        };

        this.suggestions = [];
        this.selectedIndex = -1;
        this.debounceTimer = null;
        this.dropdown = null;
        this.abortController = null;

        this.init();
    }

    init() {
        this.createDropdown();
        this.bindEvents();
        this.input.setAttribute('placeholder', this.options.placeholder);
    }

    createDropdown() {
        this.dropdown = document.createElement('div');
        this.dropdown.className = 'word-suggestion-dropdown';
        this.dropdown.setAttribute('role', 'listbox');
        this.dropdown.style.display = 'none';

        this.input.parentNode.insertBefore(this.dropdown, this.input.nextSibling);
    }

    bindEvents() {
        this.input.addEventListener('input', (e) => this.handleInput(e));
        this.input.addEventListener('keydown', (e) => this.handleKeydown(e));
        this.input.addEventListener('focus', () => this.handleFocus());
        this.input.addEventListener('blur', () => this.handleBlur());

        document.addEventListener('click', (e) => this.handleClickOutside(e));
    }

    handleInput(e) {
        const query = e.target.value.trim();

        clearTimeout(this.debounceTimer);

        if (query.length < this.options.minQueryLength || query.includes(' ')) {
            this.hideDropdown();
            return;
        }

        this.debounceTimer = setTimeout(() => {
            this.searchSuggestions(query);
        }, this.options.debounceDelay);
    }

    handleKeydown(e) {
        if (!this.dropdown.classList.contains('show')) return;

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.navigateDown();
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.navigateUp();
                break;
            case 'Enter':
                e.preventDefault();
                this.selectSuggestion();
                break;
            case 'Escape':
                e.preventDefault();
                this.hideDropdown();
                break;
        }
    }

    handleFocus() {
        if (this.suggestions.length > 0) {
            this.showDropdown();
        }
    }

    handleBlur() {
        setTimeout(() => this.hideDropdown(), 150);
    }

    handleClickOutside(e) {
        if (!this.input.contains(e.target) && !this.dropdown.contains(e.target)) {
            this.hideDropdown();
        }
    }

    async searchSuggestions(query) {
        // Cancel previous request if still running
        if (this.abortController) {
            this.abortController.abort();
        }

        this.abortController = new AbortController();
        this.showLoading();

        try {
            const response = await fetch(
                `${this.options.url}?q=${encodeURIComponent(query)}`,
                { signal: this.abortController.signal }
            );

            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

            const data = await response.json();
            this.suggestions = data.data || [];
            this.selectedIndex = -1;

            if (this.suggestions.length > 0) {
                this.renderSuggestions();
                this.showDropdown();
            } else {
                this.showEmptyState();
                this.showDropdown();
            }
        } catch (error) {
            if (error.name !== 'AbortError') {
                console.error('Error fetching suggestions:', error);
                this.showErrorState();
                this.showDropdown();
            }
        }
    }

    renderSuggestions() {
        this.dropdown.innerHTML = '';

        this.suggestions.forEach((suggestion, index) => {
            const item = this.createSuggestionItem(suggestion, index);
            this.dropdown.appendChild(item);
        });
    }

    createSuggestionItem(suggestion, index) {
        const item = document.createElement('div');
        item.className = 'word-suggestion-item';
        item.dataset.index = index;
        item.setAttribute('role', 'option');
        item.setAttribute('aria-selected', index === this.selectedIndex);

        const wordSpan = document.createElement('span');
        wordSpan.className = 'suggestion-word';
        // Handle both string suggestions and object suggestions for backward compatibility
        wordSpan.textContent = typeof suggestion === 'string' ? suggestion : suggestion.word;

        item.appendChild(wordSpan);

        item.addEventListener('click', () => this.selectSuggestion(index));

        return item;
    }

    showLoading() {
        this.dropdown.innerHTML = `
            <div class="word-suggestion-loading">
                <i class="fas fa-spinner fa-spin"></i>
                Finding suggestions...
            </div>
        `;
        this.showDropdown();
    }

    showEmptyState() {
        this.dropdown.innerHTML = `
            <div class="word-suggestion-empty">
                <i class="fas fa-search"></i>
                <p>No suggestions found for "${this.input.value}"</p>
            </div>
        `;
    }

    showErrorState() {
        this.dropdown.innerHTML = `
            <div class="word-suggestion-empty">
                <i class="fas fa-exclamation-triangle"></i>
                <p>Error loading suggestions. Please try again.</p>
            </div>
        `;
    }

    navigateDown() {
        this.selectedIndex =
            (this.selectedIndex + 1) % this.suggestions.length;
        this.updateSelection();
    }

    navigateUp() {
        this.selectedIndex =
            (this.selectedIndex - 1 + this.suggestions.length) % this.suggestions.length;
        this.updateSelection();
    }

    updateSelection() {
        const items = this.dropdown.querySelectorAll('.word-suggestion-item');
        items.forEach((item, index) => {
            const isSelected = index === this.selectedIndex;
            item.classList.toggle('selected', isSelected);
            item.setAttribute('aria-selected', isSelected);
        });
    }

    selectSuggestion(index = null) {
        const selectedIndex = index !== null ? index : this.selectedIndex;

        if (selectedIndex >= 0 && selectedIndex < this.suggestions.length) {
            const suggestion = this.suggestions[selectedIndex];
            const currentValue = this.input.value;
            const words = currentValue.split(' ');
            const lastWord = words[words.length - 1];

            // Handle both string suggestions and object suggestions for backward compatibility
            const suggestedWord = typeof suggestion === 'string' ? suggestion : suggestion.word;
            
            words[words.length - 1] = suggestedWord;
            this.input.value = words.join(' ');

            this.input.dispatchEvent(new CustomEvent('wordSelected', {
                detail: {
                    originalWord: lastWord,
                    suggestedWord: suggestedWord,
                    fullText: this.input.value
                }
            }));

            this.hideDropdown();

            // Use callback if provided
            if (typeof this.options.onSuggestionSelected === 'function') {
                this.options.onSuggestionSelected(suggestion, this.input);
            }

            // Fire global event for TableManager or others to listen
            document.dispatchEvent(new CustomEvent('reloadTable'));
        }
    }

    showDropdown() {
        this.dropdown.classList.add('show');
        this.dropdown.style.display = 'block';
    }

    hideDropdown() {
        this.dropdown.classList.remove('show');
        this.dropdown.style.display = 'none';
    }

    // Public methods
    setUrl(url) {
        this.options.url = url;
    }

    clear() {
        this.input.value = '';
        this.suggestions = [];
        this.selectedIndex = -1;
        this.hideDropdown();
    }

    destroy() {
        if (this.dropdown) this.dropdown.remove();
        if (this.debounceTimer) clearTimeout(this.debounceTimer);
        if (this.abortController) this.abortController.abort();
    }
}

// Auto-initialize
document.addEventListener('DOMContentLoaded', () => {
    const inputs = document.querySelectorAll('.word-suggestion-input');

    inputs.forEach(input => {
        const instance = new WordSuggestion(input, {
            url: input.dataset.url || '/customer/suggestions/',
            placeholder: input.dataset.placeholder || 'Type to get word suggestions...'
        });
        input.wordSuggestion = instance;
    });
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WordSuggestion;
}