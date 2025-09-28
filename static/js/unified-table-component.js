/**
 * Unified Table Component
 * A comprehensive, self-contained component for AJAX-powered tables
 * with search, sorting, pagination, filter tags, and word suggestions.
 * 
 * Combines functionality from:
 * - word-suggestion.js
 * - fetchAjax.js  
 * - filter-tags.js
 * 
 * Version: 3.0.0
 * Author: Enhanced by AI Assistant
 */

(function (window) {
    'use strict';

    // ========================================
    // UTILITY FUNCTIONS
    // ========================================

    function debounce(func, delay) {
        let timeout;
        return function (...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), delay);
        };
    }

    function createElement(tag, className = '', innerHTML = '') {
        const element = document.createElement(tag);
        if (className) 
            element.className = className;
        
        if (innerHTML) 
            element.innerHTML = innerHTML;
        
        return element;
    }

    function addEventListeners(element, events) {
        Object.entries(events).forEach(([event, handler]) => {
            element.addEventListener(event, handler);
        });
    }

    // ========================================
    // WORD SUGGESTION COMPONENT
    // ========================================

    class WordSuggestion {
        constructor(inputElement, options = {}) {
            this.input = inputElement;
            this.options = {
                debounceDelay: 300,
                minQueryLength: 2,
                maxSuggestions: 5,
                url: options.fetchUrl || (window.urls && window.urls.suggestions) || "",
                placeholder: 'Type to get word suggestions...',
                onSuggestionSelected: null,
                autoSearch: true,
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
            this.dropdown = createElement('div', 'word-suggestion-dropdown');
            this.dropdown.setAttribute('role', 'listbox');
            this.dropdown.style.display = 'none';
            this.input.parentNode.insertBefore(this.dropdown, this.input.nextSibling);
        }

        bindEvents() {
            addEventListeners(this.input, {
                'input': (e) => this.handleInput(e),
                'keydown': (e) => this.handleKeydown(e),
                'focus': () => this.handleFocus(),
                'blur': () => this.handleBlur()
            });

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
            if (!this.dropdown.classList.contains('show')) 
                return;
            

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
            if (this.abortController) {
                this.abortController.abort();
            }

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
            const item = createElement('div', 'word-suggestion-item');
            item.dataset.index = index;
            item.setAttribute('role', 'option');
            item.setAttribute('aria-selected', index === this.selectedIndex);

            const wordSpan = createElement('span', 'suggestion-word');
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
                    <p>No suggestions found for "${
                this.input.value
            }"</p>
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
            this.selectedIndex = (this.selectedIndex + 1) % this.suggestions.length;
            this.updateSelection();
        }

        navigateUp() {
            this.selectedIndex = (this.selectedIndex - 1 + this.suggestions.length) % this.suggestions.length;
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

                if (typeof this.options.onSuggestionSelected === 'function') {
                    this.options.onSuggestionSelected(suggestion, this.input);
                }

                if (this.options.autoSearch) {
                    document.dispatchEvent(new CustomEvent('reloadTable'));
                }
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
            if (this.dropdown) 
                this.dropdown.remove();
            
            if (this.debounceTimer) 
                clearTimeout(this.debounceTimer);
            
            if (this.abortController) 
                this.abortController.abort();
            
        }
    }

    // ========================================
    // FILTER TAGS MANAGER
    // ========================================

    class FilterTagsManager {
        constructor(options = {}) {
            this.options = {
                containerSelector: options.containerSelector || "#filterTagsInline",
                formSelector: options.formSelector || "#searchForm",
                ...options
            };

            this.container = document.querySelector(this.options.containerSelector);
            this.form = document.querySelector(this.options.formSelector);
            this.currentSortLabel = '';

            this.filterConfigs = this.detectFilterConfigs();
            this.init();
        }

        detectFilterConfigs() {
            const configs = {};
            if (!this.form) 
                return configs;
            

            const inputs = this.form.querySelectorAll("input, select");

            inputs.forEach(input => {
                if (input.type === "submit" || input.type === "hidden") 
                    return;
                

                const key = this.generateKey(input.id || input.name);
                const label = this.generateLabel(key);

                if (input.type === "search") {
                    configs[key] = {
                        label,
                        getValue: () => input.value || "",
                        clearValue: () => {
                            input.value = "";
                        }
                    };
                } else if (input.tagName === "SELECT") {
                    configs[key] = {
                        label,
                        getValue: () => {
                            const option = input.selectedOptions[0];
                            return option ?. value ? option.textContent : "";
                        },
                        clearValue: () => {
                            input.selectedIndex = 0;
                        }
                    };
                }
            });

            // Sorting (event-driven)
            configs.sorting = {
                label: "Sort By",
                getValue: () => this.currentSortLabel || "",
                clearValue: () => {
                    document.dispatchEvent(new CustomEvent("clearSort"));
                }
            };

            return configs;
        }

        generateKey(name) {
            return name ? name.replace(/([A-Z])/g, "_$1").toLowerCase() : "";
        }

        generateLabel(key) {
            return key.split("_").map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(" ");
        }

        formatSortValue(sortValue) {
            if (!sortValue) 
                return "";
            

            const isDescending = sortValue.startsWith("-");
            const field = isDescending ? sortValue.substring(1) : sortValue;

            const labels = {
                id: "ID",
                name: "Name",
                email: "Email",
                phone_number: "Phone",
                address: "Address",
                created_at: "Created Date",
                invoice_number: "Invoice #",
                customer__name: "Customer",
                amount: "Amount",
                payment_status: "Payment Status",
                payment_type: "Payment Type",
                invoice_date: "Invoice Date",
                due_date: "Due Date",
                updated_at: "Updated Date",
                brand: "Brand",
                category__name: "Category",
                status: "Status"
            };

            const label = labels[field] || field.replace("_", " ").replace(/\b\w/g, l => l.toUpperCase());
            return `${label} (${
                isDescending ? "Descending" : "Ascending"
            })`;
        }

        init() {
            this.bindEvents();
            this.updateTags();
        }

        bindEvents() {
            if (this.form) {
                const inputs = this.form.querySelectorAll("input, select");
                inputs.forEach(input => {
                    input.addEventListener("change", () => this.updateTags());
                    if (input.type === "search") {
                        input.addEventListener("input", debounce(() => this.updateTags(), 300));
                    }
                });
            }

            // Listen for sort changes from TableManager
            document.addEventListener("sortChanged", (e) => {
                this.currentSortLabel = this.formatSortValue(e.detail.sort);
                this.updateTags();
            });
        }

        updateTags() {
            if (!this.container) 
                return;
            
            this.container.innerHTML = "";

            const activeFilters = [];

            Object.entries(this.filterConfigs).forEach(([key, config]) => {
                const value = config.getValue();
                if (value && value.trim() !== "") {
                    activeFilters.push({key, label: config.label, value, clearValue: config.clearValue});
                }
            });

            activeFilters.forEach(filter => {
                this.container.appendChild(this.createTag(filter));
            });
        }

        createTag(filter) {
            const tag = createElement('div', 'filter-tag');
            tag.setAttribute('aria-label', `Filter: ${
                filter.label
            } ${
                filter.value
            }`);

            let display = filter.value;
            if (filter.key === "search") {
                display = `"${
                    filter.value
                }"`;
            } else if (filter.key === "sorting") {
                display = filter.value.replace(" (Ascending)", "↑").replace(" (Descending)", "↓");
            } else {
                display = `${
                    filter.label
                }: ${
                    filter.value
                }`;
            } tag.innerHTML = `
                <span>${display}</span>
                <button class="filter-tag-remove" data-filter-key="${
                filter.key
            }" aria-label="Remove filter ${
                filter.label
            }">
                    <i class="fas fa-times"></i>
                </button>
            `;

            tag.querySelector(".filter-tag-remove").addEventListener("click", () => {
                filter.clearValue();
                this.updateTags();
                document.dispatchEvent(new Event("reloadTable"));
            });

            return tag;
        }

        destroy() {
            if (this.container) 
                this.container.innerHTML = "";
            
        }
    }

    // ========================================
    // TABLE MANAGER
    // ========================================

    class TableManager {
        constructor(options = {}) {
            this.options = {
                fetchUrl: options.fetchUrl || (window.urls && window.urls.fetch) || "",
                tableSelector: options.tableSelector || ".data-table",
                bodySelector: options.bodySelector || "tbody#table_body",
                footerSelector: options.footerSelector || "tfoot#table_footer",
                paginationSelector: options.paginationSelector || "#pagination_wrapper",
                formSelector: options.formSelector || "#searchForm",
                debounceDelay: options.debounceDelay || 500,
                ...options
            };

            this.currentPage = 1;
            this.currentSort = "";
            this.tableBody = document.querySelector(this.options.bodySelector);
            this.tableFooter = document.querySelector(this.options.footerSelector);
            this.paginationWrapper = document.querySelector(this.options.paginationSelector);

            this.spinner = this.createSpinner();
            this.bindEvents();

            // Initial load
            this.loadData();
        }

        createSpinner() {
            const spinner = createElement('div', 'table-loading-spinner');
            spinner.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
                            background: var(--bg-surface); padding: 1rem; border-radius: 0.5rem;
                            box-shadow: var(--shadow-md); z-index: 9999; display: flex; align-items: center; gap: 0.5rem;">
                    <i class="fas fa-spinner fa-spin" style="color: var(--primary);"></i>
                    <span style="color: var(--text-primary);">Loading...</span>
                </div>`;
            spinner.style.display = "none";
            document.body.appendChild(spinner);
            return spinner;
        }

        showLoading() {
            const table = document.querySelector(this.options.tableSelector);
            if (table) {
                table.style.opacity = "0.6";
                table.style.pointerEvents = "none";
            }
            this.spinner.style.display = "block";
        }

        hideLoading() {
            const table = document.querySelector(this.options.tableSelector);
            if (table) {
                table.style.opacity = "1";
                table.style.pointerEvents = "auto";
            }
            this.spinner.style.display = "none";
        }

        getSearchParams() {
            const params = new URLSearchParams();
            const form = document.querySelector(this.options.formSelector);
            if (form) {
                const inputs = form.querySelectorAll("input, select");
                inputs.forEach(input => {
                    if (input.name && input.value) {
                        params.append(input.name, input.value);
                    }
                });
            }
            if (this.currentSort) 
                params.append("sort", this.currentSort);
            
            params.append("page", this.currentPage);
            return params;
        }

        async loadData() {
            if (!this.options.fetchUrl) {
                console.error("TableManager: fetchUrl not provided");
                return;
            }

            this.showLoading();
            const url = `${
                this.options.fetchUrl
            }?${
                this.getSearchParams().toString()
            }`;

            try {
                const response = await fetch(url, {
                    headers: {
                        "X-Requested-With": "XMLHttpRequest"
                    }
                });
                const data = await response.json();

                if (! data.success) 
                    throw new Error("Backend returned error");
                

                this.tableBody.innerHTML = data.html || "";
                this.paginationWrapper.innerHTML = data.pagination || "";

                this.updateSortIndicators();
            } catch (error) {
                console.error("Error loading table data:", error);
                this.tableBody.innerHTML = `
                    <tr>
                        <td colspan="8" class="text-center">
                            Error loading data.
                            <button onclick="document.dispatchEvent(new Event('reloadTable'))">Retry</button>
                        </td>
                    </tr>`;

                this.paginationWrapper.innerHTML = "";
            } finally {
                this.hideLoading();
            }
        }

        bindEvents() { // Pagination (event delegation)
            this.paginationWrapper.addEventListener("click", (e) => {
                const link = e.target.closest(".pagination .page-link");
                if (! link) 
                    return;
                
                e.preventDefault();
                const page = link.getAttribute("data-page");
                if (page) {
                    this.currentPage = parseInt(page, 10);
                    this.loadData();
                }
            });

            // Search form
            const form = document.querySelector(this.options.formSelector);
            if (form) {
                form.addEventListener("submit", (e) => {
                    e.preventDefault();
                    this.currentPage = 1;
                    this.loadData();
                });

                const searchInput = form.querySelector('input[name="search"]');
                if (searchInput) {
                    if (searchInput.classList.contains("word-suggestion-input")) {
                        searchInput.addEventListener("input", () => {
                            if (searchInput.value.trim() === "") {
                                this.currentPage = 1;
                                this.loadData();
                            }
                        });
                    } else {
                        const debouncedSearch = debounce(() => {
                            this.currentPage = 1;
                            this.loadData();
                        }, this.options.debounceDelay);
                        searchInput.addEventListener("input", debouncedSearch);
                    }
                }

                const filters = form.querySelectorAll("select");
                filters.forEach(filter => {
                    filter.addEventListener("change", () => {
                        this.currentPage = 1;
                        this.loadData();
                    });
                });
            }

            // Sorting
            const headers = document.querySelectorAll("th.sortable");
            headers.forEach(header => {
                header.addEventListener("click", () => {
                    const sortValue = header.getAttribute("data-sort");
                    if (this.currentSort === sortValue) {
                        this.currentSort = "-" + sortValue;
                    } else if (this.currentSort === "-" + sortValue) {
                        this.currentSort = sortValue;
                    } else {
                        this.currentSort = sortValue;
                    }
                    this.updateSortIndicators();
                    this.currentPage = 1;

                    document.dispatchEvent(new CustomEvent("sortChanged", {
                        detail: {
                            sort: this.currentSort
                        }
                    }));

                    this.loadData();
                });
            });

            // Listen for reloadTable event
            document.addEventListener("reloadTable", () => {
                this.currentPage = 1;
                this.loadData();
            });

            // Listen for clearSort event
            document.addEventListener("clearSort", () => {
                this.currentSort = "";
                this.updateSortIndicators();
                this.currentPage = 1;
                this.loadData();
            });
        }

        updateSortIndicators() {
            const headers = document.querySelectorAll("th.sortable");
            headers.forEach(header => {
                const sortValue = header.getAttribute("data-sort");
                header.classList.remove("active", "asc", "desc");
                header.removeAttribute("aria-sort");

                if (this.currentSort === sortValue) {
                    header.classList.add("active", "asc");
                    header.setAttribute("aria-sort", "ascending");
                } else if (this.currentSort === "-" + sortValue) {
                    header.classList.add("active", "desc");
                    header.setAttribute("aria-sort", "descending");
                } else {
                    header.setAttribute("aria-sort", "none");
                }
            });
        }
    }

    // ========================================
    // UNIFIED TABLE COMPONENT
    // ========================================

    class UnifiedTableComponent {
        constructor(container, config = {}) {
            this.container = typeof container === 'string' ? document.querySelector(container) : container;
            if (!this.container) {
                console.error(`UnifiedTableComponent: Container not found.`);
                return;
            }

            this.config = {
                fetchUrl: config.fetchUrl || (window.urls && window.urls.fetch) || "",
                suggestionUrl: config.suggestionUrl || (window.urls && window.urls.suggestions) || "",
                debounceDelay: 500,
                ...config
            };

            this.init();
        }

        init() { // Initialize components
            this.tableManager = new TableManager({fetchUrl: this.config.fetchUrl, debounceDelay: this.config.debounceDelay});

            this.filterTagsManager = new FilterTagsManager();

            // Initialize word suggestion if input exists and URL provided
            const suggestionInput = this.container.querySelector('.word-suggestion-input');
            if (suggestionInput && this.config.suggestionUrl) {
                this.wordSuggestion = new WordSuggestion(suggestionInput, {
                    url: this.config.suggestionUrl,
                    autoSearch: true
                });
            }

            // Store references for external access
            this.container.unifiedTableComponent = this;
        }

        // Public API methods
        reload() {
            document.dispatchEvent(new CustomEvent('reloadTable'));
        }

        clearFilters() {
            const form = document.querySelector('#searchForm');
            if (form) {
                const inputs = form.querySelectorAll('input, select');
                inputs.forEach(input => {
                    if (input.type === 'search') {
                        input.value = '';
                    } else if (input.tagName === 'SELECT') {
                        input.selectedIndex = 0;
                    }
                });
            }
            document.dispatchEvent(new CustomEvent('clearSort'));
            this.reload();
        }

        setSort(field, direction = 'asc') {
            const sortValue = direction === 'desc' ? `-${field}` : field;
            this.tableManager.currentSort = sortValue;
            this.tableManager.updateSortIndicators();
            this.tableManager.currentPage = 1;
            this.tableManager.loadData();
        }

        setPage(page) {
            this.tableManager.currentPage = page;
            this.tableManager.loadData();
        }

        destroy() {
            if (this.wordSuggestion) 
                this.wordSuggestion.destroy();
            
            if (this.filterTagsManager) 
                this.filterTagsManager.destroy();
            
            if (this.tableManager && this.tableManager.spinner) {
                this.tableManager.spinner.remove();
            }
        }
    }

    // ========================================
    // AUTO-INITIALIZATION
    // ========================================

    document.addEventListener('DOMContentLoaded', () => { // Auto-initialize unified table containers first
        const tableContainers = document.querySelectorAll('.unified-table-container');
        tableContainers.forEach(container => {
            if (!container.unifiedTableComponent) {
                new UnifiedTableComponent(container, {
                    fetchUrl: container.dataset.fetchUrl || (window.urls && window.urls.fetch),
                    suggestionUrl: container.dataset.suggestionUrl || (window.urls && window.urls.suggestions)
                });
            }
        });

        // Auto-initialize standalone word suggestions (only for inputs NOT inside unified containers)
        const suggestionInputs = document.querySelectorAll('.word-suggestion-input');
        suggestionInputs.forEach(input => { // Skip if input is inside a unified container (already handled)
            if (input.closest('.unified-table-container')) {
                return;
            }

            if (!input.wordSuggestion) {
                new WordSuggestion(input, {
                    url: input.dataset.url || input.dataset.fetchUrl || '/customer/suggestions/',
                    placeholder: input.dataset.placeholder || 'Type to get word suggestions...'
                });
            }
        });

        // Auto-initialize filter tags (only if no unified containers exist)
        if (! window.filterTagsManager && tableContainers.length === 0) {
            window.filterTagsManager = new FilterTagsManager();
        }
    });

    // ========================================
    // EXPOSE TO GLOBAL SCOPE
    // ========================================

    window.UnifiedTableComponent = UnifiedTableComponent;
    window.WordSuggestion = WordSuggestion;
    window.FilterTagsManager = FilterTagsManager;
    window.TableManager = TableManager;

    // Backward compatibility
    window.AjaxTableComponent = UnifiedTableComponent;

})(window);
