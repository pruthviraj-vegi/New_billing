/**
 * Unified Table Component - Usage Examples
 * 
 * This file demonstrates how to use the UnifiedTableComponent
 * in different scenarios and configurations.
 */

// ========================================
// BASIC USAGE EXAMPLES
// ========================================

// Example 1: Auto-initialization with data attributes
// HTML:
/*
<div class="unified-table-container" 
     data-fetch-url="/api/customers/" 
     data-suggestion-url="/api/suggestions/">
    <div class="search-filter-section">
        <form id="searchForm">
            <input type="search" name="search" class="word-suggestion-input" 
                   placeholder="Search customers...">
            <select name="status">
                <option value="">All Status</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
            </select>
        </form>
    </div>
    <div id="filterTagsInline" class="filter-tags-container"></div>
    <div class="table-container">
        <table class="data-table">
            <thead>
                <tr>
                    <th class="sortable" data-sort="name">Name</th>
                    <th class="sortable" data-sort="email">Email</th>
                    <th class="sortable" data-sort="created_at">Created</th>
                </tr>
            </thead>
            <tbody id="table_body"></tbody>
        </table>
    </div>
    <div id="pagination_wrapper" class="pagination-wrapper"></div>
</div>
*/

// Example 2: Manual initialization
document.addEventListener('DOMContentLoaded', function() {
    const container = document.querySelector('#my-table-container');
    
    const tableComponent = new UnifiedTableComponent(container, {
        fetchUrl: '/api/customers/',
        suggestionUrl: '/api/suggestions/',
        debounceDelay: 300
    });
    
    // Access component methods
    tableComponent.reload();
    tableComponent.clearFilters();
    tableComponent.setSort('name', 'asc');
    tableComponent.setPage(2);
});

// ========================================
// ADVANCED CONFIGURATION EXAMPLES
// ========================================

// Example 3: Custom word suggestion configuration
const customSuggestion = new WordSuggestion(document.querySelector('#custom-search'), {
    fetchUrl: '/api/custom-suggestions/',
    debounceDelay: 500,
    minQueryLength: 3,
    maxSuggestions: 10,
    placeholder: 'Type at least 3 characters...',
    onSuggestionSelected: function(suggestion, input) {
        console.log('Selected:', suggestion);
        // Custom logic after suggestion selection
    }
});

// Example 4: Standalone filter tags manager
const filterManager = new FilterTagsManager({
    containerSelector: '#custom-filter-tags',
    formSelector: '#custom-search-form'
});

// Example 5: Standalone table manager
const tableManager = new TableManager({
    fetchUrl: '/api/products/',
    tableSelector: '.products-table',
    bodySelector: '#products-tbody',
    paginationSelector: '#products-pagination',
    formSelector: '#product-search-form',
    debounceDelay: 400
});

// ========================================
// EVENT HANDLING EXAMPLES
// ========================================

// Example 6: Custom event listeners
document.addEventListener('reloadTable', function() {
    console.log('Table is being reloaded');
    // Custom logic when table reloads
});

document.addEventListener('sortChanged', function(event) {
    console.log('Sort changed to:', event.detail.sort);
    // Custom logic when sort changes
});

document.addEventListener('clearSort', function() {
    console.log('Sort cleared');
    // Custom logic when sort is cleared
});

// Example 7: Word suggestion events
document.querySelector('.word-suggestion-input').addEventListener('wordSelected', function(event) {
    console.log('Word selected:', event.detail);
    // event.detail contains:
    // - originalWord: the word that was replaced
    // - suggestedWord: the word that was selected
    // - fullText: the complete input value
});

// ========================================
// INTEGRATION WITH EXISTING CODE
// ========================================

// Example 8: Integration with existing AJAX code
function loadCustomerData() {
    // Your existing AJAX code
    fetch('/api/customers/')
        .then(response => response.json())
        .then(data => {
            // Update table
            document.querySelector('#table_body').innerHTML = data.html;
            
            // Trigger table reload event for filter tags
            document.dispatchEvent(new CustomEvent('reloadTable'));
        });
}

// Example 9: Dynamic URL updates
function updateTableUrl(newUrl) {
    const container = document.querySelector('.unified-table-container');
    if (container.unifiedTableComponent) {
        container.unifiedTableComponent.tableManager.options.fetchUrl = newUrl;
        container.unifiedTableComponent.reload();
    }
}

// ========================================
// CUSTOM STYLING EXAMPLES
// ========================================

// Example 10: Custom CSS classes
// Add these to your CSS file:

/*
.custom-table-container {
    border: 2px solid #e2e8f0;
    border-radius: 1rem;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.custom-filter-tag {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 20px;
    padding: 0.25rem 0.75rem;
    font-size: 0.8rem;
}

.custom-suggestion-dropdown {
    border: 2px solid #667eea;
    border-radius: 0.75rem;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
}
*/

// ========================================
// ERROR HANDLING EXAMPLES
// ========================================

// Example 11: Error handling
const tableComponent = new UnifiedTableComponent('#error-prone-container', {
    fetchUrl: '/api/might-fail/',
    suggestionUrl: '/api/suggestions/'
});

// Override the loadData method for custom error handling
const originalLoadData = tableComponent.tableManager.loadData;
tableComponent.tableManager.loadData = async function() {
    try {
        await originalLoadData.call(this);
    } catch (error) {
        console.error('Custom error handling:', error);
        // Show custom error message
        this.tableBody.innerHTML = `
            <tr>
                <td colspan="100%" class="text-center text-danger">
                    <i class="fas fa-exclamation-triangle"></i>
                    Custom error message: ${error.message}
                </td>
            </tr>
        `;
    }
};

// ========================================
// PERFORMANCE OPTIMIZATION EXAMPLES
// ========================================

// Example 12: Debounced search with custom delay
const optimizedTable = new UnifiedTableComponent('#optimized-table', {
    fetchUrl: '/api/large-dataset/',
    debounceDelay: 1000, // 1 second delay for large datasets
    suggestionUrl: '/api/suggestions/'
});

// Example 13: Lazy loading with intersection observer
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const container = entry.target;
            if (!container.unifiedTableComponent) {
                new UnifiedTableComponent(container, {
                    fetchUrl: container.dataset.fetchUrl,
                    suggestionUrl: container.dataset.suggestionUrl
                });
            }
            observer.unobserve(container);
        }
    });
});

document.querySelectorAll('.lazy-table-container').forEach(container => {
    observer.observe(container);
});

// ========================================
// MIGRATION FROM OLD COMPONENTS
// ========================================

// Example 14: Migrating from separate components
// Old way:
/*
const wordSuggestion = new WordSuggestion(input, options);
const tableManager = new TableManager(options);
const filterTagsManager = new FilterTagsManager(options);
*/

// New way:
const unifiedComponent = new UnifiedTableComponent(container, {
    fetchUrl: options.fetchUrl,
    suggestionUrl: options.suggestionUrl,
    debounceDelay: options.debounceDelay
});

// Access individual components if needed:
// unifiedComponent.wordSuggestion
// unifiedComponent.tableManager
// unifiedComponent.filterTagsManager

// ========================================
// TESTING EXAMPLES
// ========================================

// Example 15: Unit testing helpers
function createTestTableComponent(config = {}) {
    const container = document.createElement('div');
    container.className = 'unified-table-container';
    container.innerHTML = `
        <div class="search-filter-section">
            <form id="searchForm">
                <input type="search" name="search" class="word-suggestion-input">
            </form>
        </div>
        <div id="filterTagsInline" class="filter-tags-container"></div>
        <div class="table-container">
            <table class="data-table">
                <tbody id="table_body"></tbody>
            </table>
        </div>
        <div id="pagination_wrapper" class="pagination-wrapper"></div>
    `;
    
    document.body.appendChild(container);
    
    return new UnifiedTableComponent(container, {
        fetchUrl: '/test-api/',
        suggestionUrl: '/test-suggestions/',
        ...config
    });
}

// Example 16: Mock API responses for testing
function mockApiResponse(data) {
    return {
        success: true,
        html: data.html || '<tr><td>Test data</td></tr>',
        pagination: data.pagination || '<div class="pagination">Test pagination</div>'
    };
}
