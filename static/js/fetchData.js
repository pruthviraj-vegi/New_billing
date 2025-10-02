/**
 * AJAX Table & Word Suggestion Utilities
 *
 * Why this approach?
 * - Keeps frontend lightweight by using backend-rendered HTML only
 * - Uses AbortController to cancel stale requests → avoids race conditions
 * - Debounced input handling → prevents spamming the backend
 * - Accessible: aria-busy, aria-live, keyboard-friendly
 * - Retry handling with one-time listeners
 * - jQuery-like wrapper `$()` for easy integration without full jQuery
 *
 * Key Exposed Methods:
 * - loadTableData(formId, tableId, fetchUrl, options) → Fetch & render table
 * - initTableAjax(formId, tableId, fetchUrl, options, inputSearch) → Attach to form
 * - reloadTable(tableId) → Reload using cached config
 * - $(selector).ajax({ ... }) → Initialize table ajax via wrapper
 * - $(selector).wordSuggestion({ ... }) → Initialize word suggestion
 */

const tableAjaxConfigs = {};
const tableAbortControllers = {};

// 🔹 Debounce utility (fix: preserve caller context via function, not arrow)
function debounce(fn, delay) {
    let timer;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}

// 🔹 Load table data with specific page
async function loadTableDataWithPage(formId, tableId, fetchUrl, options = {}, page = 1) {
    const form = document.getElementById(formId);
    const table = document.getElementById(tableId);

    if (! form || ! table || !fetchUrl) 
        return false;
    


    const tableBody = table.querySelector("tbody");
    const paginationWrapper = document.getElementById(`${tableId}_pagination`) || document.querySelector(`#${tableId} + .pagination-wrapper`) || document.querySelector(".pagination-wrapper");

    // Cancel previous request if still running
    if (tableAbortControllers[tableId]) {
        tableAbortControllers[tableId].abort();
    }
    const abortController = new AbortController();
    tableAbortControllers[tableId] = abortController;

    showTableLoading(table, options.loadingText || "Loading...");

    try {         // Collect form inputs
        const params = new URLSearchParams();
        const inputs = form.querySelectorAll("input, select, textarea");
        inputs.forEach((input) => {
            if (input.name && input.value && input.value.trim() !== "") {
                params.append(input.name, input.value.trim());
            }
        });

        // Add sort parameter if available
        const tableElement = document.getElementById(tableId);
        if (tableElement && tableElement.dataset.sort) {
            params.append('sort', tableElement.dataset.sort);
            console.log('Sort parameter added:', tableElement.dataset.sort);
        } else {
            console.log('No sort parameter found for table:', tableId);
        }

        // Add page parameter
        params.append('page', page);

        // Build request
        const requestOptions = {
            method: options.method || "GET",
            headers: {
                "X-Requested-With": "XMLHttpRequest"
            },
            signal: abortController.signal
        };
        let url = fetchUrl;
        if (requestOptions.method.toUpperCase() === "POST") {
            requestOptions.body = params;
            requestOptions.headers["Content-Type"] = "application/x-www-form-urlencoded";
        } else {
            url = `${fetchUrl}?${
                params.toString()
            }`;
        }

        // Fetch data
        const response = await fetch(url, requestOptions);
        if (! response.ok) 
            throw new Error(`HTTP error! Status: ${
                response.status
            }`);
        


        const data = await response.json();
        if (! data.success) 
            throw new Error("Backend returned error");
        


        // Replace table body
        if (tableBody) 
            tableBody.innerHTML = data.html || "";
        


        // Replace pagination
        if (paginationWrapper) {
            paginationWrapper.innerHTML = data.pagination || "";

            // Add click handlers to pagination links
            paginationWrapper.addEventListener('click', function (e) {
                if (e.target.closest('a[data-page]')) {
                    e.preventDefault();
                    const page = e.target.closest('a[data-page]').getAttribute('data-page');
                    loadTableDataWithPage(formId, tableId, fetchUrl, options, page);
                }
            });
        }

        // Dispatch event on table itself (not document)
        table.dispatchEvent(new CustomEvent("tableDataLoaded", {
            detail: {
                formId,
                tableId,
                data
            }
        }));

        if (typeof options.onSuccess === "function") {
            options.onSuccess(data, table);
        }

        return true;
    } catch (error) {
        if (error.name === "AbortError") 
            return false;
        


        console.error(`Error loading table ${tableId}:`, error);

        if (tableBody) {
            const colCount = table.querySelector("thead tr") ?. children.length || 1;
            const errorRow = document.createElement("tr");
            errorRow.innerHTML = `
                <td colspan="${colCount}" class="text-center">
                    ${
                options.errorText || "Error loading data."
            }
                    <button class="btn btn-sm btn-outline-primary retry-btn">
                        ${
                options.retryText || "Retry"
            }
                    </button>
                </td>
            `;
            tableBody.innerHTML = "";
            tableBody.appendChild(errorRow);

            const retryBtn = errorRow.querySelector(".retry-btn");
            retryBtn.addEventListener("click", () => loadTableData(formId, tableId, fetchUrl, options), {once: true});
        }
        if (paginationWrapper) 
            paginationWrapper.innerHTML = "";
        


        if (typeof options.onError === "function") {
            options.onError(error, table);
        }

        return false;
    } finally {
        hideTableLoading(table);
    }
}

// 🔹 Load table data (core function)
async function loadTableData(formId, tableId, fetchUrl, options = {}) {
    const form = document.getElementById(formId);
    const table = document.getElementById(tableId);

    if (! form || ! table || !fetchUrl) 
        return false;
    


    const tableBody = table.querySelector("tbody");
    const paginationWrapper = document.getElementById(`${tableId}_pagination`) || document.querySelector(`#${tableId} + .pagination-wrapper`) || document.querySelector(".pagination-wrapper");

    // Cancel previous request if still running
    if (tableAbortControllers[tableId]) {
        tableAbortControllers[tableId].abort();
    }
    const abortController = new AbortController();
    tableAbortControllers[tableId] = abortController;

    showTableLoading(table, options.loadingText || "Loading...");

    try {         // Collect form inputs
        const params = new URLSearchParams();
        const inputs = form.querySelectorAll("input, select, textarea");
        inputs.forEach((input) => {
            if (input.name && input.value && input.value.trim() !== "") {
                params.append(input.name, input.value.trim());
            }
        });

        // Add sort parameter if available
        const tableElement = document.getElementById(tableId);
        if (tableElement && tableElement.dataset.sort) {
            params.append('sort', tableElement.dataset.sort);
            console.log('Sort parameter added:', tableElement.dataset.sort);
        } else {
            console.log('No sort parameter found for table:', tableId);
        }

        // Build request
        const requestOptions = {
            method: options.method || "GET",
            headers: {
                "X-Requested-With": "XMLHttpRequest"
            },
            signal: abortController.signal
        };
        let url = fetchUrl;
        if (requestOptions.method.toUpperCase() === "POST") {
            requestOptions.body = params;
            requestOptions.headers["Content-Type"] = "application/x-www-form-urlencoded";
        } else {
            url = `${fetchUrl}?${
                params.toString()
            }`;
        }

        // Fetch data
        const response = await fetch(url, requestOptions);
        if (! response.ok) 
            throw new Error(`HTTP error! Status: ${
                response.status
            }`);
        


        const data = await response.json();
        if (! data.success) 
            throw new Error("Backend returned error");
        


        // Replace table body
        if (tableBody) 
            tableBody.innerHTML = data.html || "";
        


        // Replace pagination
        if (paginationWrapper) {
            paginationWrapper.innerHTML = data.pagination || "";

            // Add click handlers to pagination links
            paginationWrapper.addEventListener('click', function (e) {
                if (e.target.closest('a[data-page]')) {
                    e.preventDefault();
                    const page = e.target.closest('a[data-page]').getAttribute('data-page');
                    loadTableDataWithPage(formId, tableId, fetchUrl, options, page);
                }
            });
        }

        // Dispatch event on table itself (not document)
        table.dispatchEvent(new CustomEvent("tableDataLoaded", {
            detail: {
                formId,
                tableId,
                data
            }
        }));

        if (typeof options.onSuccess === "function") {
            options.onSuccess(data, table);
        }

        return true;
    } catch (error) {
        if (error.name === "AbortError") 
            return false;
        


        console.error(`Error loading table ${tableId}:`, error);

        if (tableBody) {
            const colCount = table.querySelector("thead tr") ?. children.length || 1;
            const errorRow = document.createElement("tr");
            errorRow.innerHTML = `
                <td colspan="${colCount}" class="text-center">
                    ${
                options.errorText || "Error loading data."
            }
                    <button class="btn btn-sm btn-outline-primary retry-btn">
                        ${
                options.retryText || "Retry"
            }
                    </button>
                </td>
            `;
            tableBody.innerHTML = "";
            tableBody.appendChild(errorRow);

            const retryBtn = errorRow.querySelector(".retry-btn");
            retryBtn.addEventListener("click", () => loadTableData(formId, tableId, fetchUrl, options), {once: true});
        }
        if (paginationWrapper) 
            paginationWrapper.innerHTML = "";
        


        if (typeof options.onError === "function") {
            options.onError(error, table);
        }

        return false;
    } finally {
        hideTableLoading(table);
    }
}

// 🔹 Show loading spinner
function showTableLoading(table, loadingText) {
    if (table) {
        table.style.opacity = "0.6";
        table.style.pointerEvents = "none";
        table.setAttribute("aria-busy", "true");
    }

    let spinner = document.getElementById(`${
        table.id
    }-loading`);
    if (! spinner) {
        spinner = document.createElement("div");
        spinner.id = `${
            table.id
        }-loading`;
        spinner.className = "table-spinner"; // CSS-based styling
        spinner.setAttribute("role", "status");
        spinner.setAttribute("aria-live", "polite");
        spinner.innerHTML = `
            <i class="fas fa-spinner fa-spin"></i>
            <span>${loadingText}</span>
        `;
        document.body.appendChild(spinner);
    }
    spinner.style.display = "flex";
}

// 🔹 Hide loading spinner
function hideTableLoading(table) {
    if (table) {
        table.style.opacity = "1";
        table.style.pointerEvents = "auto";
        table.setAttribute("aria-busy", "false");
    }
    const spinner = document.getElementById(`${
        table.id
    }-loading`);
    if (spinner) 
        spinner.style.display = "none";
    


}

// 🔹 Initialize AJAX for form + table
function initTableAjax(formId, tableId, fetchUrl, options = {}, inputSearch = false) {
    tableAjaxConfigs[tableId] = {
        formId,
        tableId,
        fetchUrl,
        options
    };

    const form = document.getElementById(formId);
    if (form) { // Submit event → AJAX load
        form.addEventListener("submit", (e) => {
            e.preventDefault();
            loadTableData(formId, tableId, fetchUrl, options);
        });

        // Attach input listeners
        let inputs = inputSearch ? form.querySelectorAll("input, select, textarea") : form.querySelectorAll("select, textarea");

        inputs.forEach((input) => input.addEventListener("input", debounce(() => loadTableData(formId, tableId, fetchUrl, options), options.debounceDelay || 400)));
    }

    // Optional initial load
    if (options.autoLoad !== false) {
        loadTableData(formId, tableId, fetchUrl, options);
    }
}

// 🔹 Reload table by ID
function reloadTable(tableId) {
    const config = tableAjaxConfigs[tableId];
    if (config) {
        loadTableData(config.formId, config.tableId, config.fetchUrl, config.options);
    } else {
        console.error(`No AJAX config found for table '${tableId}'`);
    }
}

// 🔹 Lightweight wrapper (jQuery-like)
function $(selector) {
    const elements = typeof selector === "string" ? document.querySelectorAll(selector) : [selector];
    return {
        wordSuggestion: function (options = {}) {
            elements.forEach((element) => {
                if (!element) 
                    return;
                


                const config = {
                    url: options.url || "",
                    placeholder: options.placeholder || "Type to search...",
                    minLength: options.minLength || 2,
                    debounceDelay: options.debounceDelay || 300,
                    maxSuggestions: options.maxSuggestions || 5,
                    onSelect: options.onSelect || null,
                    ...options
                };
                if (! config.url) {
                    console.error("WordSuggestion: URL is required");
                    return;
                }
                initWordSuggestion(element, config.url, {
                    debounceDelay: config.debounceDelay,
                    minQueryLength: config.minLength,
                    maxSuggestions: config.maxSuggestions,
                    onSuggestionSelected: config.onSelect
                });
            });
            return this;
        },
        ajax: function (options = {}) {
            elements.forEach((element) => {
                if (!element || element.tagName !== "FORM") {
                    console.error("Table AJAX: Element must be a form");
                    return;
                }
                const config = {
                    tableId: options.tableId || "",
                    url: options.url || "",
                    placeholder: options.placeholder || "Loading...",
                    method: options.method || "GET",
                    debounceDelay: options.debounceDelay || 400,
                    includeInputs: options.includeInputs || false,
                    autoLoad: options.autoLoad !== false,
                    sortable: options.sortable !== true, // Default true
                    onSuccess: options.onSuccess || null,
                    onError: options.onError || null,
                    ...options
                };
                if (! config.tableId || ! config.url) {
                    console.error("Table AJAX: tableId and url are required");
                    return;
                }
                initTableAjax(element.id, config.tableId, config.url, {
                    method: config.method,
                    debounceDelay: config.debounceDelay,
                    loadingText: config.placeholder,
                    autoLoad: config.autoLoad,
                    onSuccess: config.onSuccess,
                    onError: config.onError
                }, config.includeInputs);
                
                // Initialize sorting if enabled
                if (config.sortable) {
                    initTableSorting(config.tableId);
                }
            });
            return this;
        }
    };
}

// 🔹 Initialize table sorting
function initTableSorting(tableId) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const sortableHeaders = table.querySelectorAll('th[data-sort]');
    
    sortableHeaders.forEach(header => {
        header.style.cursor = 'pointer';
        header.addEventListener('click', function() {
            const sortField = this.getAttribute('data-sort');
            const currentSort = table.dataset.sort || '';
            
            let newSort;
            if (currentSort === sortField) {
                // Currently ascending, switch to descending
                newSort = '-' + sortField;
            } else if (currentSort === '-' + sortField) {
                // Currently descending, clear sort
                newSort = '';
            } else {
                // New field, start ascending
                newSort = sortField;
            }
            
            // Update table sort state
            table.dataset.sort = newSort;
            console.log('Table sort updated to:', newSort);
            
            // Update visual indicators
            updateSortIndicators(table, newSort);
            
            // Dispatch sort changed event for filter tags
            document.dispatchEvent(new CustomEvent('sortChanged', {
                detail: { sort: newSort }
            }));
            
            // Reload table with new sort
            reloadTable(tableId);
        });
    });
}

// 🔹 Update sort visual indicators
function updateSortIndicators(table, sortValue) {
    const headers = table.querySelectorAll('th[data-sort]');
    
    headers.forEach(header => {
        const field = header.getAttribute('data-sort');
        
        // Remove all sort classes
        header.classList.remove('active', 'asc', 'desc');
        
        // Add appropriate class based on sort state
        if (sortValue === field) {
            header.classList.add('active', 'asc');
        } else if (sortValue === '-' + field) {
            header.classList.add('active', 'desc');
        }
    });
}

// 🔹 Expose globally
window.loadTableData = loadTableData;
window.loadTableDataWithPage = loadTableDataWithPage;
window.initTableAjax = initTableAjax;
window.reloadTable = reloadTable;
window.initTableSorting = initTableSorting;
window.updateSortIndicators = updateSortIndicators;
window.$ = $;
