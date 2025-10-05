/**
 * Select2 Initialization Helper
 * Ensures Select2 is available before initializing forms
 */

window.Select2Helper = {
    // Check if Select2 is available
    isAvailable: function () {
        return typeof $ !== 'undefined' && typeof $.fn !== 'undefined' && typeof $.fn.select2 !== 'undefined';
    },

    // Wait for Select2 to be available
    waitForSelect2: function (callback, maxAttempts = 50) {
        let attempts = 0;
        const self = this;

        function check() {
            attempts++;
            if (self.isAvailable()) {
                callback();
            } else if (attempts < maxAttempts) {
                setTimeout(check, 100);
            } else {
                console.warn('Select2 failed to load after maximum attempts');
            }
        }

        check();
    },

    // Initialize Select2 on specific elements
    init: function (selectors, options = {}) {
        const defaultOptions = {
            placeholder: "Type to search...",
            allowClear: true,
            width: '100%'
        };

        const finalOptions = Object.assign({}, defaultOptions, options);

        this.waitForSelect2(() => {
            $(selectors).select2(finalOptions);
        });
    },

    // Initialize with custom options
    initCustom: function (selectors, customOptions) {
        this.waitForSelect2(() => {
            $(selectors).each(function () {
                const $this = $(this);
                const options = Object.assign({}, customOptions);
                $this.select2(options);
            });
        });
    },

    // Initialize all form selects (only if Select2 is available)
    initAllForms: function () {
        this.waitForSelect2(() => {
            // Only initialize selects that have specific classes or are in forms that need Select2
            $('select[id^="id_"][class*="select2"], select[data-select2="true"]').each(function () {
                const $this = $(this);
                if (!$this.hasClass('select2-hidden-accessible')) {
                    $this.select2({
                        placeholder: "Type to search...",
                        allowClear: true,
                        width: '100%'
                    });
                }
            });
        });
    }
};

// Auto-initialize on DOM ready (only if Select2 is needed)
document.addEventListener('DOMContentLoaded', function () {
    // Check if there are any forms that actually need Select2
    const needsSelect2 = document.querySelector('select[id^="id_"][class*="select2"], select[data-select2="true"]');

    if (needsSelect2) {
        // Wait for jQuery to be available
        function waitForJQuery() {
            if (typeof $ !== 'undefined') {
                // Small delay to ensure all scripts are loaded
                setTimeout(function () {
                    Select2Helper.initAllForms();
                }, 200);
            } else {
                setTimeout(waitForJQuery, 100);
            }
        }
        waitForJQuery();
    }
});
