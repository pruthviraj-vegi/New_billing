/**
 * Filter Tags Manager
 * 
 * Improvements:
 * - Event-driven (listens for "sortChanged" & "reloadTable" instead of polling)
 * - Caches input elements for performance
 * - Uses CustomEvents for table reload requests
 * - Accessible tags (aria-labels)
 * - Consistent with WordSuggestion + TableManager
 */

class FilterTagsManager {
    constructor(options = {}) {
        this.options = {
            containerSelector: options.containerSelector || "#filterTagsInline",
            formSelector: options.formSelector || "#searchForm"
        };

        this.container = document.querySelector(this.options.containerSelector);
        this.form = document.querySelector(this.options.formSelector);

        this.filterConfigs = this.detectFilterConfigs();
        this.init();
    }

    detectFilterConfigs() {
        const configs = {};
        if (!this.form) return configs;

        const inputs = this.form.querySelectorAll("input, select");

        inputs.forEach(input => {
            if (input.type === "submit" || input.type === "hidden") return;

            const key = this.generateKey(input.id || input.name);
            const label = this.generateLabel(key);

            if (input.type === "search") {
                configs[key] = {
                    label,
                    getValue: () => input.value || "",
                    clearValue: () => { input.value = ""; }
                };
            } else if (input.tagName === "SELECT") {
                configs[key] = {
                    label,
                    getValue: () => {
                        const option = input.selectedOptions[0];
                        return option?.value ? option.textContent : "";
                    },
                    clearValue: () => { input.selectedIndex = 0; }
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
        return key
            .split("_")
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(" ");
    }

    formatSortValue(sortValue) {
        if (!sortValue) return "";

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
        return `${label} (${isDescending ? "Descending" : "Ascending"})`;
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
                    input.addEventListener("input", this.debounce(() => this.updateTags(), 300));
                }
            });
        }

        // Listen for sort changes from TableManager
        document.addEventListener("sortChanged", (e) => {
            this.currentSortLabel = this.formatSortValue(e.detail.sort);
            this.updateTags();
        });
    }

    debounce(fn, delay) {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => fn.apply(this, args), delay);
        };
    }

    updateTags() {
        if (!this.container) return;
        this.container.innerHTML = "";

        const activeFilters = [];

        Object.entries(this.filterConfigs).forEach(([key, config]) => {
            const value = config.getValue();
            if (value && value.trim() !== "") {
                activeFilters.push({ key, label: config.label, value, clearValue: config.clearValue });
            }
        });

        activeFilters.forEach(filter => {
            this.container.appendChild(this.createTag(filter));
        });
    }

    createTag(filter) {
        const tag = document.createElement("div");
        tag.className = "filter-tag";
        tag.setAttribute("aria-label", `Filter: ${filter.label} ${filter.value}`);

        let display = filter.value;
        if (filter.key === "search") {
            display = `"${filter.value}"`;
        } else if (filter.key === "sorting") {
            display = filter.value.replace(" (Ascending)", "↑").replace(" (Descending)", "↓");
        } else {
            display = `${filter.label}: ${filter.value}`;
        }

        tag.innerHTML = `
            <span>${display}</span>
            <button class="filter-tag-remove" data-filter-key="${filter.key}" aria-label="Remove filter ${filter.label}">
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
        // Nothing to poll now → just clean container
        this.container.innerHTML = "";
    }
}

// Auto-init
document.addEventListener("DOMContentLoaded", () => {
    window.filterTagsManager = new FilterTagsManager();
});