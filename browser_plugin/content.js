// Blooming Rewrite Engine 2.0 - Content Script
// Runs on web pages to provide writing assistance

(function() {
    console.log('Blooming Rewrite Engine 2.0 - Content script loaded');
    
    // Listen for messages from popup
    chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
        if (request.action === 'get-selected-text') {
            const selectedText = window.getSelection().toString();
            sendResponse({text: selectedText});
        } else if (request.action === 'show-suggestion') {
            showSuggestion(request.suggestion);
        }
        return true;
    });
    
    function showSuggestion(suggestion) {
        // Create suggestion popup
        const popup = document.createElement('div');
        popup.id = 'blooming-suggestion-popup';
        popup.innerHTML = `
            <div style="
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: white;
                border: 2px solid #4CAF50;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                z-index: 10000;
                max-width: 500px;
                font-family: Arial, sans-serif;
            ">
                <h3 style="margin-top: 0; color: #4CAF50;">
                    🌸 Writing Suggestion
                </h3>
                <p style="margin: 5px 0; font-size: 12px; color: #666;">
                    ${suggestion.suggestion_type}
                </p>
                <div style="background: #f5f5f5; padding: 10px; border-radius: 5px; margin: 10px 0;">
                    <strong>Original:</strong><br>
                    <span style="color: #666;">${suggestion.original_text}</span>
                </div>
                <div style="background: #E8F5E9; padding: 10px; border-radius: 5px; margin: 10px 0;">
                    <strong>Suggested:</strong><br>
                    <span style="color: #2E7D32;">${suggestion.suggested_text}</span>
                </div>
                <p style="font-size: 13px; color: #555;">
                    <strong>Why:</strong> ${suggestion.explanation}
                </p>
                <div style="margin-top: 15px; text-align: right;">
                    <button id="reject-suggestion" style="
                        padding: 8px 16px;
                        margin-right: 10px;
                        border: 1px solid #ddd;
                        background: white;
                        border-radius: 5px;
                        cursor: pointer;
                    ">Reject</button>
                    <button id="accept-suggestion" style="
                        padding: 8px 16px;
                        background: #4CAF50;
                        color: white;
                        border: none;
                        border-radius: 5px;
                        cursor: pointer;
                    ">Accept</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(popup);
        
        // Add event listeners
        document.getElementById('accept-suggestion').addEventListener('click', function() {
            acceptSuggestion(suggestion);
            popup.remove();
        });
        
        document.getElementById('reject-suggestion').addEventListener('click', function() {
            rejectSuggestion(suggestion);
            popup.remove();
        });
    }
    
    function acceptSuggestion(suggestion) {
        // Replace selected text with suggestion
        // (Implementation depends on editable element type)
        console.log('Accepted:', suggestion);
        
        // Could integrate with contentEditable, textarea, etc.
    }
    
    function rejectSuggestion(suggestion) {
        console.log('Rejected:', suggestion);
    }
})();

