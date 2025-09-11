/**
 * Optimized Table AJAX Loader
 * 
 * Improvements:
 * - Wrapped logic into a TableManager class (no more globals)
 * - Debounce utility for consistent behavior
 * - Loading spinner created once and toggled (less DOM churn)
 * - Event delegation for pagination
 * - Added ARIA attributes for sorting headers
 * - Listens for "reloadTable" custom event (from WordSuggestion)
 */

class TableManager {
    constructor(options = {}) {
        this.options = {
            fetchUrl: options.fetchUrl || (window.urls && window.urls.fetch) || "",
            tableSelector: options.tableSelector || ".data-table",
            bodySelector: options.bodySelector || "tbody#table_body",
            footerSelector: options.footerSelector || "tfoot#table_footer",
            paginationSelector: options.paginationSelector || "#pagination_wrapper",
            formSelector: options.formSelector || "#searchForm",
            debounceDelay: options.debounceDelay || 500
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

    // Utility: debounce
    debounce(fn, delay) {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => fn.apply(this, args), delay);
        };
    }

    // Create spinner once
    createSpinner() {
        const spinner = document.createElement("div");
        spinner.id = "table-loading";
        spinner.innerHTML = `
            <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
                        background: var(--bg-surface); padding: 1rem; border-radius: 0.5rem;
                        box-shadow: var(--shadow-md); z-index: 9999; display: flex; align-items: center; gap: 0.5rem;">
                <i class="fas fa-spinner fa-spin" style="color: var(--primary);"></i>
                <span style="color: var(--text-primary);">Loading customers...</span>
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
        if (this.currentSort) params.append("sort", this.currentSort);
        params.append("page", this.currentPage);
        return params;
    }

    async loadData() {
        if (!this.options.fetchUrl) {
            console.error("TableManager: fetchUrl not provided");
            return;
        }

        this.showLoading();
        const url = `${this.options.fetchUrl}?${this.getSearchParams().toString()}`;

        try {
            const response = await fetch(url, {
                headers: { "X-Requested-With": "XMLHttpRequest" }
            });
            const data = await response.json();

            if (!data.success) throw new Error("Backend returned error");

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

    bindEvents() {
        // Pagination (event delegation)
        this.paginationWrapper.addEventListener("click", (e) => {
            const link = e.target.closest(".pagination .page-link");
            if (!link) return;
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
                    // Suggestion input → rely on WordSuggestion events
                    searchInput.addEventListener("input", () => {
                        if (searchInput.value.trim() === "") {
                            this.currentPage = 1;
                            this.loadData();
                        }
                    });
                } else {
                    // Regular debounced search
                    const debouncedSearch = this.debounce(() => {
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
                
                // Dispatch sort changed event for FilterTagsManager
                document.dispatchEvent(new CustomEvent("sortChanged", {
                    detail: { sort: this.currentSort }
                }));
                
                this.loadData();
            });
        });

        // Listen for reloadTable event (from WordSuggestion or retry button)
        document.addEventListener("reloadTable", () => {
            this.currentPage = 1;
            this.loadData();
        });

        // Listen for clearSort event (from FilterTagsManager)
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

// Auto-initialize
document.addEventListener("DOMContentLoaded", () => {
    window.tableManager = new TableManager({
        fetchUrl: urls.fetch // assumes global urls.fetch exists
    });
});