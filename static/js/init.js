document.addEventListener("DOMContentLoaded", () => {
    console.log("Initializing Customers Management...");

    // Wait for TableManager to be initialized
    const checkTableManager = () => {
        if (window.tableManager) {
            console.log("✅ TableManager found, initializing integration...");
            
            // The TableManager and FilterTagsManager are auto-initialized
            // WordSuggestion is also auto-initialized
            // No additional setup needed - they communicate via events
            
            console.log("✅ Customers Management initialized with new architecture.");
        } else {
            console.log("⏳ Waiting for TableManager...");
            setTimeout(checkTableManager, 100);
        }
    };
    
    checkTableManager();
});
