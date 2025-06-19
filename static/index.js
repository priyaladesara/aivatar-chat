let socket;
let isConnected = false;
// phase1-wotnot
let visitorId = null;
let threadId = null;
let currentVisitorId = null;
// phase2-heygen
let heygenSocket = null;
let heygenWsUrl = null;
let heygenRealtimeUrl = null;
let heygenSessionId = null;
let heygenAccessToken = null;
let heygenRoomConnected = false;
let liveKitRoom = null; // Store room reference

function updateConnectionStatus(status, className) {
    const statusElement = document.getElementById('connection-status');
    statusElement.textContent = status;
    statusElement.className = `status ${className}`;
}

// Initialize WebSocket connection
function initializeSocket() {
    socket = io();
    
    socket.on('connect', function() {
        console.log('Connected to WebSocket');
        isConnected = true;
        updateConnectionStatus('Connected', 'connected');
        
        if (visitorId) {
            socket.emit('join', {visitor_id: visitorId});
        }
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnected from WebSocket');
        isConnected = false;
        updateConnectionStatus('Disconnected', 'disconnected');
    });
    
    socket.on('new_message', function(data) {
        console.log('New message received via WebSocket:', data);
        if (data.visitor_id === visitorId || data.visitor_id === currentVisitorId) {
            displayMessage(data.message, true);
        }
    });

    socket.on('avatar_speak', function(data) {
        console.log('Avatar speak event received:', data);
    });
}

// Join the WebSocket room when chat starts
function joinChatRoom(visitorId) {
    currentVisitorId = visitorId;
    if (socket && isConnected) {
        socket.emit('join', { visitor_id: visitorId });
    }
}

// Fixed LiveKit connection using correct URL
async function connectToHeyGenLiveKit() {
    if (heygenRoomConnected || !heygenWsUrl || !heygenAccessToken) {
        console.log("Cannot connect to HeyGen LiveKit:", {
            alreadyConnected: heygenRoomConnected,
            hasWsUrl: !!heygenWsUrl,
            hasToken: !!heygenAccessToken,
            wsUrl: heygenWsUrl
        });
        return;
    }

    if (!window.LivekitClient || !window.LivekitClient.Room) {
        console.error("LiveKit client not available");
        return;
    }

    heygenRoomConnected = true;

    try {
        const { Room } = window.LivekitClient;
        const videoElement = document.getElementById("heygen-video");

        if (!videoElement) {
            console.error("Video element not found");
            heygenRoomConnected = false;
            return;
        }

        liveKitRoom = new Room();

        liveKitRoom.on('trackSubscribed', (track, publication, participant) => {
            console.log("Track subscribed:", track.kind, "from", participant.identity);
            
            if (track.kind === 'video') {
                track.attach(videoElement);
                // lastchange
                  // CRITICAL AUDIO FIX: Configure video element for audio
                videoElement.muted = false;  // Must be false for audio
                videoElement.volume = 1.0;   // Set volume to maximum
                videoElement.autoplay = true;
                videoElement.playsInline = true;
                videoElement.controls = false; // Remove for production
                
                // Handle browser autoplay policy
                videoElement.play().then(() => {
                    console.log("Video with audio started successfully");
                }).catch((error) => {
                    console.error("Autoplay blocked, showing play button:", error);
                    showAudioPlayButton();
                });

                showVideoContainer();
                console.log("Video track attached to element");
            }
             // Handle audio tracks separately if they exist
            if (track.kind === 'audio') {
                console.log("Audio track received");
                track.attach(videoElement);
                videoElement.muted = false;
                videoElement.volume = 1.0;
            }
        });

        liveKitRoom.on('participantConnected', (participant) => {
            console.log("✅ Participant connected:", participant.identity);
        });

        liveKitRoom.on('disconnected', () => {
            console.log("Disconnected from HeyGen LiveKit");
            heygenRoomConnected = false;
            hideVideoContainer();
        });

        liveKitRoom.on('connectionStateChanged', (state) => {
            console.log("LiveKit connection state:", state);
        });

        console.log("Connecting to HeyGen LiveKit room...");
        console.log("LiveKit URL:", heygenWsUrl);
        console.log("Access Token:", heygenAccessToken ? "Present" : "Missing");
        
        // Connect using LiveKit URL and access token
        await liveKitRoom.connect(heygenWsUrl, heygenAccessToken);
        console.log("Connected to HeyGen LiveKit room successfully");

    } catch (error) {
        console.error("LiveKit connection error:", error);
        heygenRoomConnected = false;
    }
}


function showVideoContainer() {
    const videoContainer = document.getElementById('heygen-video-container');
    const videoElement = document.getElementById('heygen-video');
    
    if (videoContainer && videoElement) {
        videoContainer.style.display = 'block';
        videoElement.style.display = 'block';
        
        // Ensure audio settings are correct when showing
        videoElement.muted = false;
        videoElement.volume = 1.0;
        videoElement.autoplay = true;
        
        console.log("Video container shown with audio enabled");
    }
}

function hideVideoContainer() {
    const videoContainer = document.getElementById('heygen-video-container');
    const videoElement = document.getElementById('heygen-video');
    
    if (videoContainer && videoElement) {
        videoContainer.style.display = 'none';
        videoElement.style.display = 'none';
        console.log("Video container hidden");
    }
}

// Fixed WebRTC initialization using realtime endpoint
async function initHeyGenWebRTC() {
    if (!heygenRealtimeUrl) {
        console.log("Missing HeyGen realtime URL for WebSocket");
        return;
    }

    try {
        // Close existing connection if any
        if (heygenSocket && heygenSocket.readyState === WebSocket.OPEN) {
            heygenSocket.close();
        }

        console.log("Connecting to HeyGen WebSocket:", heygenRealtimeUrl);
        
        // Use realtime endpoint directly
        heygenSocket = new WebSocket(heygenRealtimeUrl);

        heygenSocket.onopen = () => {
            console.log("HeyGen WebSocket connected");
            
            // Send authentication after connection opens
            if (heygenAccessToken) {
                const authMessage = {
                    type: "authenticate",
                    data: {
                        access_token: heygenAccessToken
                    }
                };
                heygenSocket.send(JSON.stringify(authMessage));
                console.log("Sent authentication to HeyGen WebSocket");
            }
        };

        heygenSocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log("HeyGen message received:", data);

                if (data.type === 'playback_url') {
                    const videoUrl = data.data?.url;
                    if (videoUrl) {
                        showHeyGenVideo(videoUrl);
                    }
                }
            } catch (error) {
                console.error("Error parsing HeyGen message:", error);
            }
        };

        heygenSocket.onerror = (error) => {
            console.error("HeyGen WebSocket error:", error);
        };

        heygenSocket.onclose = (event) => {
            console.log("HeyGen WebSocket closed:", event.code, event.reason);
        };

    } catch (error) {
        console.error("Failed to initialize HeyGen WebRTC:", error);
    }
}
// last-update-4
function showHeyGenVideo(videoUrl) {
    const videoElement = document.getElementById('heygen-video');
    if (videoElement && videoUrl) {
        videoElement.src = videoUrl;
        
        // Configure audio before playing
        videoElement.muted = false;
        videoElement.volume = 1.0;
        videoElement.autoplay = true;
        videoElement.playsInline = true;
        
        // Try to play with audio
        videoElement.play().then(() => {
            console.log("HeyGen video playing with audio");
        }).catch(error => {
            console.error("Autoplay blocked for HeyGen video:", error);
            showAudioPlayButton();
        });
        
        showVideoContainer();
        console.log("HeyGen video URL set with audio:", videoUrl);
    }
}

// fix for mobile browser-optional but neeeded - not rechecked yet.
function enableAudioContext() {
    // Handle Web Audio API context suspension
    if (typeof AudioContext !== 'undefined' || typeof webkitAudioContext !== 'undefined') {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        const audioContext = new AudioContext();
        
        if (audioContext.state === 'suspended') {
            console.log('Audio context suspended, will resume on user interaction');
            
            const resumeAudio = () => {
                audioContext.resume().then(() => {
                    console.log('Audio context resumed');
                });
                document.removeEventListener('click', resumeAudio);
                document.removeEventListener('touchstart', resumeAudio);
            };
            
            document.addEventListener('click', resumeAudio, { once: true });
            document.addEventListener('touchstart', resumeAudio, { once: true });
        }
    }
}

// Fixed startChat function with proper credential handling
async function startChat() {
    try {
        const response = await fetch('/api/start-chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();
        console.log("Start chat response:", data);

        if (data.success) {
            visitorId = data.visitor_id;
            threadId = data.thread_id;
            currentVisitorId = data.visitor_id;

            // Check if HeyGen credentials are present and properly formatted
            if (data.heygen && Object.keys(data.heygen).length > 0) {
                console.log("HeyGen data received:", data.heygen);
                
                // Extract credentials from the correct fields
                heygenSessionId = data.heygen.session_id;
                heygenAccessToken = data.heygen.access_token;
                
                // Use 'url' field for LiveKit connection
                heygenWsUrl = data.heygen.url;
                
                // Use 'realtime_endpoint' for WebRTC signaling
                heygenRealtimeUrl = data.heygen.realtime_endpoint;

                console.log("HeyGen credentials set:", {
                    sessionId: heygenSessionId ? "Present" : "Missing",
                    accessToken: heygenAccessToken ? "Present" : "Missing",
                    liveKitUrl: heygenWsUrl || "Missing",
                    realtimeUrl: heygenRealtimeUrl || "Missing"
                });

                // Only initialize if we have the required credentials
                if (heygenSessionId && heygenAccessToken && heygenWsUrl && heygenRealtimeUrl) {
                    console.log("Initializing HeyGen connections...");
                    
                    // Initialize connections with small delay
                    setTimeout(async () => {
                        await initHeyGenWebRTC();
                        await connectToHeyGenLiveKit();
                    }, 500);
                } else {
                    console.warn("Missing required HeyGen credentials");
                }
            } else {
                console.warn("HeyGen credentials not received in response");
                console.log("Full response data:", data);
            }

            // Show chat screen
            document.getElementById('start-screen').style.display = 'none';
            const chatScreen = document.getElementById('chat-screen');
            chatScreen.style.display = 'flex';
            chatScreen.style.flexDirection = 'column';
            chatScreen.style.flex = '1';

            joinChatRoom(visitorId);

            if (data.initial_message) {
                displayMessage({
                    type: 'bot',
                    message: data.initial_message,
                    timestamp: new Date().toISOString()
                });
            }

            window.currentVisitorId = visitorId;
            document.getElementById('message-input').focus();
        } else {
            alert('Failed to start chat: ' + data.error);
        }
    } catch (error) {
        console.error('Error starting chat:', error);
        alert('Error starting chat: ' + error.message);
    }
}

async function sendMessage(messageText) {
    const messageInput = document.getElementById('message-input');
    const message = messageText || messageInput.value.trim();
    
    if (!message || (!window.currentVisitorId && !visitorId)) return;
    
    // Display user message immediately
    displayMessage({
        type: 'user',
        message: message,
        timestamp: new Date().toISOString()
    });
    
    if (messageInput) {
        messageInput.value = '';
    }
    
    // Disable send button temporarily
    const sendButton = document.getElementById('send-button');
    if (sendButton) {
        sendButton.disabled = true;
    }
    
    try {
        const response = await fetch('/api/send-message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                visitor_id: window.currentVisitorId || visitorId,
                message: message
            })
        });
        
        const data = await response.json();
        
        if (!data.success) {
            alert('Failed to send message: ' + data.error);
        }
        
    } catch (error) {
        console.error('Error sending message:', error);
        alert('Error sending message: ' + error.message);
    } finally {
        if (sendButton) {
            sendButton.disabled = false;
        }
        if (messageInput) {
            messageInput.focus();
        }
    }
}

// Enhanced display message function to handle buttons
function displayMessage(message, fromWebhook = false) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');

    // Handle both old and new message formats
    const messageType = message.type || 'bot';
    const messageText = message.message || message;
    const timestamp = message.timestamp || new Date().toISOString();

    messageDiv.className = `message ${messageType}-message`;

    const time = new Date(timestamp).toLocaleTimeString();
    const webhookIndicator = fromWebhook ? '<div class="webhook-indicator">via webhook</div>' : '';

    let buttonsHtml = '';
    if (message.buttons && message.buttons.length > 0) {
        buttonsHtml = `
            <div class="buttons">
                ${message.buttons.map(btn => 
                    `<button class="chat-button" onclick="sendButtonResponse('${btn.title}')">${btn.title}</button>`
                ).join('')}
            </div>
        `;
    }

    messageDiv.innerHTML = `
        <div class="message-text">${messageText}</div>
        ${buttonsHtml}
        <div class="timestamp">${time}</div>
        ${webhookIndicator}
    `;

    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Only trigger HeyGen for bot messages
    if (messageType === 'bot') {
        sendTextToHeyGen(messageText);
    }
}

function sendTextToHeyGen(text) {
    if (heygenSocket && heygenSocket.readyState === WebSocket.OPEN) {
        const payload = {
            type: "text_input",
            data: {
                text: text
            }
        };
        
        heygenSocket.send(JSON.stringify(payload));
        console.log("Sent text to HeyGen:", text);
    } else {
        console.warn("HeyGen WebSocket not ready. State:", heygenSocket?.readyState);
    }
}

// Fixed beforeunload event handler
window.addEventListener('beforeunload', function (e) {
    if (visitorId) {
        const data = JSON.stringify({ visitor_id: visitorId });
        const blob = new Blob([data], { type: 'application/json' });
        navigator.sendBeacon('/api/stop-chat', blob);
    }
    
    // Clean up connections
    if (liveKitRoom) {
        liveKitRoom.disconnect();
    }
    if (heygenSocket) {
        heygenSocket.close();
    }
});

async function stopChat() {
    if (!visitorId) return;
    
    try {
        // Clean up connections first
        if (liveKitRoom) {
            liveKitRoom.disconnect();
            liveKitRoom = null;
        }
        
        if (heygenSocket) {
            heygenSocket.close();
            heygenSocket = null;
        }
        
        hideVideoContainer();
        
        const response = await fetch('/api/stop-chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ visitor_id: visitorId })
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log('Chat stopped successfully');
            // Reset the UI
            document.getElementById('chat-screen').style.display = 'none';
            document.getElementById('start-screen').style.display = 'block';
            
            // Reset variables
            visitorId = null;
            currentVisitorId = null;
            heygenRoomConnected = false;
            heygenSessionId = null;
            heygenAccessToken = null;
            heygenWsUrl = null;
            heygenRealtimeUrl = null;
        } else {
            console.error('Failed to stop chat:', data.error);
        }
    } catch (error) {
        console.error('Error stopping chat:', error);
    }
}

// Function to send button responses
function sendButtonResponse(buttonText) {
    sendMessage(buttonText);
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM loaded, initializing...");
    
    // Wait for LiveKit to load properly
    let attempts = 0;
    const maxAttempts = 10;
    
    const checkLiveKit = () => {
        attempts++;
        if (window.LivekitClient || window.LiveKitClient) {
            console.log("LiveKit is available");
            // Normalize the reference
            if (!window.LivekitClient && window.LiveKitClient) {
                window.LivekitClient = window.LiveKitClient;
            }
            initializeSocket();
        } else if (attempts < maxAttempts) {
            console.log(`Waiting for LiveKit... attempt ${attempts}`);
            setTimeout(checkLiveKit, 200);
        } else {
            console.error("LiveKit failed to load after all attempts");
            initializeSocket(); // Continue without LiveKit
        }
    };
    
    checkLiveKit();
});