// Blooming Rewrite Engine 2.0 - Browser Plugin
// Popup Script

let websocket = null;
let connected = false;

document.addEventListener('DOMContentLoaded', function () {
    const connectBtn = document.getElementById('connect-btn');
    const suggestBtn = document.getElementById('request-suggestions-btn');
    const createProjectBtn = document.getElementById('create-project-btn');
    const saveIdeaBtn = document.getElementById('save-idea-btn');
    const statusDiv = document.getElementById('status');

    // Connect button handler
    connectBtn.addEventListener('click', function () {
        if (connected) {
            disconnect();
        } else {
            connect();
        }
    });

    // Suggest button handler
    suggestBtn.addEventListener('click', function () {
        requestSuggestions();
    });

    // Create Project button handler
    createProjectBtn.addEventListener('click', function () {
        sendSelection('create_project');
    });

    // Save Idea button handler
    saveIdeaBtn.addEventListener('click', function () {
        sendSelection('save_idea');
    });

    // Check initial connection status
    checkConnectionStatus();
});

function sendSelection(actionType) {
    if (!connected || !websocket) {
        alert('Not connected to server');
        return;
    }

    chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
        chrome.tabs.sendMessage(tabs[0].id, {
            action: 'get-selected-text'
        }, function (response) {
            if (response && response.text) {
                const message = {
                    type: actionType,
                    text: response.text,
                    source_url: tabs[0].url,
                    title: tabs[0].title
                };
                websocket.send(JSON.stringify(message));

                // Show feedback
                const btn = actionType === 'create_project' ?
                    document.getElementById('create-project-btn') :
                    document.getElementById('save-idea-btn');

                const originalText = btn.textContent;
                btn.textContent = 'Sent!';
                setTimeout(() => {
                    btn.textContent = originalText;
                }, 2000);
            } else {
                alert('Please select some text first.');
            }
        });
    });
}

function connect() {
    try {
        websocket = new WebSocket('ws://localhost:8080/ws');

        websocket.onopen = function () {
            connected = true;
            updateConnectionStatus(true);
            console.log('Connected to Blooming Rewrite Engine');
        };

        websocket.onmessage = function (event) {
            handleMessage(JSON.parse(event.data));
        };

        websocket.onerror = function (error) {
            console.error('WebSocket error:', error);
            updateConnectionStatus(false);
        };

        websocket.onclose = function () {
            connected = false;
            updateConnectionStatus(false);
            console.log('Disconnected from server');
        };

    } catch (error) {
        console.error('Connection failed:', error);
        alert('Failed to connect. Make sure the WebSocket server is running.');
    }
}

function disconnect() {
    if (websocket) {
        websocket.close();
        websocket = null;
        connected = false;
        updateConnectionStatus(false);
    }
}

function updateConnectionStatus(isConnected) {
    const statusDiv = document.getElementById('status');
    const connectBtn = document.getElementById('connect-btn');
    const suggestBtn = document.getElementById('request-suggestions-btn');
    const createProjectBtn = document.getElementById('create-project-btn');
    const saveIdeaBtn = document.getElementById('save-idea-btn');

    if (isConnected) {
        statusDiv.className = 'connection-status connected';
        statusDiv.textContent = '✅ Connected';
        connectBtn.textContent = 'Disconnect';
        suggestBtn.disabled = false;
        createProjectBtn.disabled = false;
        saveIdeaBtn.disabled = false;
    } else {
        statusDiv.className = 'connection-status disconnected';
        statusDiv.textContent = '❌ Not Connected';
        connectBtn.textContent = 'Connect to Server';
        suggestBtn.disabled = true;
        createProjectBtn.disabled = true;
        saveIdeaBtn.disabled = true;
    }
}

function requestSuggestions() {
    if (!connected || !websocket) {
        alert('Not connected to server');
        return;
    }

    // Send message to content script to get selected text
    chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
        chrome.tabs.sendMessage(tabs[0].id, {
            action: 'get-selected-text'
        }, function (response) {
            if (response && response.text) {
                // Send to WebSocket server
                const message = {
                    type: 'request_suggestions',
                    paragraph: response.text,
                    context: {
                        authenticity_level: document.getElementById('authenticity-level').value,
                        rewrite_mode: document.getElementById('rewrite-mode').value
                    }
                };

                websocket.send(JSON.stringify(message));
            }
        });
    });
}

function handleMessage(message) {
    if (message.type === 'connected') {
        console.log('Session ID:', message.session_id);
    } else if (message.type === 'suggestion') {
        // Forward suggestion to content script
        chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
            chrome.tabs.sendMessage(tabs[0].id, {
                action: 'show-suggestion',
                suggestion: message.suggestion
            });
        });
    }
}

function checkConnectionStatus() {
    // Check if server is available
    // (This is a simplified check)
}

