// Blooming Rewrite Engine 2.0 - Background Script
// Manages WebSocket connection and state

let websocket = null;
let connected = false;

chrome.runtime.onInstalled.addListener(function() {
    console.log('Blooming Rewrite Engine 2.0 installed');
});

// Handle messages from popup and content scripts
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
    if (request.action === 'connect') {
        connectToServer();
        sendResponse({success: true});
    } else if (request.action === 'disconnect') {
        disconnectFromServer();
        sendResponse({success: true});
    } else if (request.action === 'send-message') {
        if (websocket && connected) {
            websocket.send(JSON.stringify(request.message));
            sendResponse({success: true});
        } else {
            sendResponse({success: false, error: 'Not connected'});
        }
    }
    return true;
});

function connectToServer() {
    try {
        websocket = new WebSocket('ws://localhost:8765');
        
        websocket.onopen = function() {
            connected = true;
            console.log('Connected to Blooming Rewrite Engine server');
            notifyConnectionStatus(true);
        };
        
        websocket.onmessage = function(event) {
            const message = JSON.parse(event.data);
            handleServerMessage(message);
        };
        
        websocket.onerror = function(error) {
            console.error('WebSocket error:', error);
            connected = false;
            notifyConnectionStatus(false);
        };
        
        websocket.onclose = function() {
            connected = false;
            notifyConnectionStatus(false);
        };
        
    } catch (error) {
        console.error('Failed to connect:', error);
    }
}

function disconnectFromServer() {
    if (websocket) {
        websocket.close();
        websocket = null;
        connected = false;
    }
}

function handleServerMessage(message) {
    // Forward to all content scripts
    chrome.tabs.query({}, function(tabs) {
        tabs.forEach(tab => {
            chrome.tabs.sendMessage(tab.id, {
                action: 'server-message',
                message: message
            });
        });
    });
}

function notifyConnectionStatus(isConnected) {
    chrome.runtime.sendMessage({
        action: 'connection-status-changed',
        connected: isConnected
    });
}

