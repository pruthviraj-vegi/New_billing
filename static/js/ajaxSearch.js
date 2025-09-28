/**
 * AjaxTableComponent
 * A self-contained, reusable component for creating AJAX-powered tables
 * with search, sorting, pagination, filter tags, and word suggestions.
 *
 * Version: 2.0.0 (JavaScript Initialization)
 * Author: Gemini
 */

(function (window) {
    'use strict';

    // --- UTILITY FUNCTIONS --- //
    function debounce(func, delay) {
        let timeout;
        return function (...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), delay);
        };
    }

    // --- COMPONENT CLASSES (Internal) --- //

    class WordSuggestion {
        constructor(inputElement, options = {}) {
            this.input = inputElement;
            this.container = options.container || document.body;
            this.options = {
                debounceDelay: 300,
                minQueryLength: 2,
                url: options.fetchUrl || "",
                autoSearch: options.autoSearch !== false, // Default to true unless explicitly false
                ...options
            };
            this.abortController = null;
            this.init();
        }

        init() {
            this.createDropdown();
            this.bindEvents();
            this.input.setAttribute('placeholder', this.options.placeholder || 'Type for suggestions...');
        }

        createDropdown() {
            this.dropdown = document.createElement('div');
            this.dropdown.className = 'word-suggestion-dropdown';
            this.dropdown.setAttribute('role', 'listbox');
            this.dropdown.style.display = 'none';
            this.input.parentNode.insertBefore(this.dropdown, this.input.nextSibling);
        }

        bindEvents() {
            this.input.addEventListener('input', debounce((e) => this.handleInput(e), this.options.debounceDelay));
            this.input.addEventListener('keydown', (e) => this.handleKeydown(e));
            document.addEventListener('click', (e) => {
                if (!this.input.contains(e.target) && !this.dropdown.contains(e.target)) {
                    this.hideDropdown();
                }
            });
        }

        handleInput(e) {
            const query = e.target.value.trim();
            if (query.length < this.options.minQueryLength || query.includes(' ')) {
                this.hideDropdown();
                return;
            }
            this.searchSuggestions(query);
        }

        handleKeydown(e) {
            if (this.dropdown.style.display === 'none' || !this.suggestions || this.suggestions.length === 0) 
                return;
            
            switch (e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    this.selectedIndex = (this.selectedIndex + 1) % this.suggestions.length;
                    this.updateSelection();
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    this.selectedIndex = (this.selectedIndex - 1 + this.suggestions.length) % this.suggestions.length;
                    this.updateSelection();
                    break;
                case 'Enter':
                    e.preventDefault();
                    this.selectSuggestion();
                    break;
                case 'Escape':
                    this.hideDropdown();
                    break;
            }
        }

        async searchSuggestions(query) {
            if (this.abortController) 
                this.abortController.abort();
            
            this.abortController = new AbortController();
            this.showLoading();
            try {
                const response = await fetch(`${
                    this.options.url
                }?q=${
                    encodeURIComponent(query)
                }`, {signal: this.abortController.signal});
                if (! response.ok) 
                    throw new Error(`HTTP error! status: ${
                        response.status
                    }`);
                
                const data = await response.json();
                this.suggestions = data.data || [];
                this.selectedIndex = -1;
                this.renderSuggestions();
            } catch (error) {
                if (error.name !== 'AbortError') {
                    console.error('Error fetching suggestions:', error);
                    this.showErrorState();
                }
            }
        }

        renderSuggestions() {
            this.dropdown.innerHTML = '';
            if (this.suggestions.length > 0) {
                this.suggestions.forEach((suggestion, index) => {
                    const item = document.createElement('div');
                    item.className = 'word-suggestion-item';
                    item.textContent = typeof suggestion === 'string' ? suggestion : suggestion.word;
                    item.dataset.index = index;
                    item.addEventListener('mousedown', () => this.selectSuggestion(index));
                    this.dropdown.appendChild(item);
                });
                this.showDropdown();
            } else {
                this.hideDropdown();
            }
        }

        updateSelection() {
            this.dropdown.querySelectorAll('.word-suggestion-item').forEach((item, index) => {
                item.classList.toggle('selected', index === this.selectedIndex);
            });
        }

        selectSuggestion(index = null) {
            const selectedIndex = index !== null ? index : this.selectedIndex;
            if (selectedIndex > -1 && this.suggestions[selectedIndex]) {
                const suggestion = this.suggestions[selectedIndex];
                const suggestedWord = typeof suggestion === 'string' ? suggestion : suggestion.word;
                const words = this.input.value.split(' ');
                words[words.length - 1] = suggestedWord;
                this.input.value = words.join(' ') + ' ';
                this.hideDropdown();
                if (this.options.autoSearch) {
                    this.container.dispatchEvent(new CustomEvent('reloadTable'));
                }
            }
        }
        showLoading() {
            this.dropdown.innerHTML = `<div class="word-suggestion-loading">Loading...</div>`;
            this.showDropdown();
        }
        showErrorState() {
            this.dropdown.innerHTML = `<div class="word-suggestion-empty">Error loading.</div>`;
            this.showDropdown();
        }
        showDropdown() {
            this.dropdown.style.display = 'block';
        }
        hideDropdown() {
            this.dropdown.style.display = 'none';
        }
    }

    class FilterTagsManager {
        constructor(container) {
            this.container = container;
            this.tagsContainer = container.querySelector('.filter-tags-container');
            this.form = container.querySelector('form');
            if (!this.tagsContainer || !this.form) {
                console.warn("FilterTagsManager could not find required elements.");
                return;
            }
            this.init();
        }
        init() {
            this.bindEvents();
            this.updateTags();
        }
        bindEvents() {
            this.form.addEventListener('change', () => this.updateTags());
            this.form.querySelectorAll('input[type="search"]').forEach(input => input.addEventListener('input', debounce(() => this.updateTags(), 300)));
            this.container.addEventListener('sortChanged', () => this.updateTags());
        }
        updateTags() {
            this.tagsContainer.innerHTML = '';
            const formData = new FormData(this.form);
            for (const [name, value] of formData.entries()) {
                if (value) {
                    const input = this.form.querySelector(`[name="${name}"]`);
                    let label = input.dataset.label || name;
                    let displayValue = value;
                    if (input.tagName === 'SELECT') 
                        displayValue = input.options[input.selectedIndex].text;
                    
                    this.createTag(label, displayValue, () => this.clearInput(name));
                }
            }
            const sortState = this.container.dataset.currentSort;
            if (sortState) {
                const isDesc = sortState.startsWith('-');
                const field = isDesc ? sortState.substring(1) : sortState;
                const label = this.container.querySelector(`th[data-sort="${field}"]`) ?. textContent || field;
                this.createTag(
                    'Sort',
                    `${label} ${
                        isDesc ? '↓' : '↑'
                    }`,
                    () => this.container.dispatchEvent(new CustomEvent('clearSort'))
                );
            }
        }
        createTag(label, value, onRemove) {
            const tag = document.createElement('div');
            tag.className = 'filter-tag';
            tag.innerHTML = `<span class="filter-tag-label">${label}:</span> <span class="filter-tag-value">${value}</span> <button type="button" class="filter-tag-remove">&times;</button>`;
            tag.querySelector('.filter-tag-remove').addEventListener('click', () => {
                onRemove();
                this.container.dispatchEvent(new CustomEvent('reloadTable'));
            });
            this.tagsContainer.appendChild(tag);
        }
        clearInput(name) {
            const input = this.form.querySelector(`[name="${name}"]`);
            if (input) {
                if (input.tagName === 'SELECT') 
                    input.selectedIndex = 0;
                 else 
                    input.value = '';
                
            }
        }
    }

    class TableManager {
        constructor(container, options = {}) {
            this.container = container;
            this.options = {
                debounceDelay: 500,
                ...options
            };
            this.tableBody = container.querySelector('.data-table-body');
            this.paginationWrapper = container.querySelector('.pagination-wrapper');
            this.form = container.querySelector('form');
            if (!this.tableBody || !this.paginationWrapper || !this.form) {
                throw new Error("TableManager could not find required elements.");
            }
            this.currentPage = 1;
            this.currentSort = '';
            this.spinner = this.createSpinner();
            this.bindEvents();
            this.loadData();
        }
        createSpinner() {
            const spinner = document.createElement('div');
            spinner.className = 'table-loading-spinner';
            spinner.style.display = 'none';
            this.container.style.position = 'relative';
            this.container.appendChild(spinner);
            return spinner;
        }
        showLoading() {
            this.spinner.style.display = 'flex';
            this.container.style.opacity = '0.7';
        }
        hideLoading() {
            this.spinner.style.display = 'none';
            this.container.style.opacity = '1';
        }
        bindEvents() {
            this.form.addEventListener('submit', e => e.preventDefault());
            this.form.addEventListener('change', () => {
                this.currentPage = 1;
                this.loadData();
            });
            const searchInput = this.form.querySelector('input[type="search"]');
            if (searchInput && ! searchInput.classList.contains('word-suggestion-input')) {
                searchInput.addEventListener('input', debounce(() => {
                    this.currentPage = 1;
                    this.loadData();
                }, this.options.debounceDelay));
            }
            this.paginationWrapper.addEventListener('click', e => {
                const link = e.target.closest('a[data-page]');
                if (link) {
                    e.preventDefault();
                    this.currentPage = parseInt(link.dataset.page, 10);
                    this.loadData();
                }
            });
            this.container.querySelectorAll('th[data-sort]').forEach(header => {
                header.addEventListener('click', () => {
                    const sortValue = header.dataset.sort;
                    this.currentSort = this.currentSort === sortValue ? `-${sortValue}` : sortValue;
                    this.currentPage = 1;
                    this.loadData();
                });
            });
            this.container.addEventListener('reloadTable', () => {
                this.currentPage = 1;
                this.loadData();
            });
            this.container.addEventListener('clearSort', () => {
                this.currentSort = '';
                this.currentPage = 1;
                this.loadData();
            });
        }
        getSearchParams() {
            const params = new URLSearchParams(new FormData(this.form));
            params.append('page', this.currentPage);
            if (this.currentSort) {
                params.append('sort', this.currentSort);
            }
            return params.toString();
        }
        async loadData() {
            if (!this.options.fetchUrl) {
                console.error("TableManager: fetchUrl not provided.");
                return;
            }
            this.showLoading();
            try {
                const url = `${
                    this.options.fetchUrl
                }?${
                    this.getSearchParams()
                }`;
                const response = await fetch(url, {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                const data = await response.json();
                if (! data.success) 
                    throw new Error(data.error || "Backend error");
                
                this.tableBody.innerHTML = data.html;
                this.paginationWrapper.innerHTML = data.pagination;
                this.updateSortIndicators();
                this.container.dataset.currentSort = this.currentSort;
                this.container.dispatchEvent(new CustomEvent('sortChanged'));
            } catch (error) {
                console.error("Error loading data:", error);
                this.tableBody.innerHTML = `<tr><td colspan="100%" class="text-center text-danger">Error loading data.</td></tr>`;
            } finally {
                this.hideLoading();
            }
        }
        updateSortIndicators() {
            this.container.querySelectorAll("th[data-sort]").forEach(header => {
                const sortValue = header.dataset.sort;
                header.classList.remove("sort-asc", "sort-desc");
                if (this.currentSort === sortValue) 
                    header.classList.add("sort-asc");
                 else if (this.currentSort === `-${sortValue}`) 
                    header.classList.add("sort-desc");
                
            });
        }
    }

    // --- MAIN PUBLIC CLASSES --- //
    class AjaxTableComponent {
        constructor(container, config) {
            this.container = typeof container === 'string' ? document.querySelector(container) : container;
            if (!this.container) {
                console.error(`AjaxTableComponent: Container not found.`);
                return;
            }
            this.config = config;
            this.tableManager = new TableManager(this.container, {fetchUrl: this.config.fetchUrl});
            this.filterTagsManager = new FilterTagsManager(this.container);
            const suggestionInput = this.container.querySelector('.word-suggestion-input');
            if (suggestionInput && this.config.suggestionUrl) {
                this.wordSuggestion = new WordSuggestion(suggestionInput, {
                    fetchUrl: this.config.suggestionUrl,
                    container: this.container,
                    autoSearch: true // Always true for the full component
                });
            }
        }
    }

    // Expose the main classes to the window object for manual initialization
    window.AjaxTableComponent = AjaxTableComponent;
    window.WordSuggestion = WordSuggestion;

})(window);
