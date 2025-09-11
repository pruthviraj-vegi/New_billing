/**
 * Reusable Popup System for Django Models
 * Usage: openModelPopup(url, paramName, fieldId)
 */

// Generic popup function
function openModelPopup(url, paramName, fieldId) {
    const popup = window.open(url + '?popup=1', 'addModel', 'width=600,height=500,scrollbars=yes,resizable=yes,status=yes,location=no,toolbar=no,menubar=no,top=100,left=100')

    // Focus the popup window
    if (popup) {
        popup.focus()
    }

    // Listen for popup close and refresh the page
    const checkClosed = setInterval(function () {
        if (popup.closed) {
            clearInterval(checkClosed)
            // Small delay to ensure URL parameters are set
            setTimeout(function () {
                location.reload()
            }, 200)
        }
    }, 1000)
}

// Simple function to refresh page when popup closes
function refreshOnPopupClose() {
    // This function is called when popup closes
    // The parent page will reload automatically via popup.js
}

// Export functions for global use
window.openModelPopup = openModelPopup
window.refreshOnPopupClose = refreshOnPopupClose
