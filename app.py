from flask import Flask, request, jsonify, render_template
import json
import uuid
from datetime import datetime
import re
from flask_socketio import SocketIO, join_room
import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
socketio = SocketIO(app, cors_allowed_origins="*")

# WotNot API Configuration
WOTNOT_BASE_URL = os.getenv("WOTNOT_BASE_URL")
WOTNOT_API_KEY = os.getenv("WOTNOT_API_KEY")
BOT_KEY = os.getenv("BOT_KEY")
WEBHOOK_TOKEN = os.getenv("WEBHOOK_TOKEN")

# HeyGen configuration
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")
HEYGEN_BASE_URL = os.getenv("HEYGEN_BASE_URL")

# Avatar configuration
DEFAULT_AVATAR_ID = os.getenv("DEFAULT_AVATAR_ID")
DEFAULT_VOICE_ID = os.getenv("DEFAULT_VOICE_ID")
avatar_id = DEFAULT_AVATAR_ID
voice_id = DEFAULT_VOICE_ID

from wotnot_client import WotNotAPI
from heygen_client import HeyGenStreamingClient


# In-memory storage for conversation threads 
conversation_threads = {}
# NEW: Add mapping between WotNot conversation IDs and local visitor IDs
wotnot_to_local_mapping = {}
# heygen session 
heygen_sessions = {} 


def clean_publish_key(key):
    """Clean publish key by removing special characters, emojis, and whitespace"""
    key = key.strip()
    key = re.sub(r'[^a-zA-Z0-9]', '', key)
    return key

def strip_html_tags(text):
    """Strip HTML tags from text"""
    if not text:
        return ""
    return re.sub(r'<[^>]+>', '', text).strip()


# ---------------------------------------------------------------------------------------------------------------------------
# DONOT TOUCH-----------------------------------
#---------------------------------------------------------------------------------------------------------------------------
# Initialize WotNot API client
wotnot_client = WotNotAPI(WOTNOT_API_KEY, BOT_KEY ,WOTNOT_BASE_URL)

@app.route('/')
def index():
    """Serve the main chat interface"""
    return render_template('index.html')

def handle_conversation_creation_event(event_data):
    """Handle conversation creation events"""
    try:
        conversation = event_data.get('conversation', {})
        visitor = event_data.get('visitor', {})
        
        conversation_key = str(conversation.get('key'))
        visitor_key = visitor.get('key')
        
        print(f"New conversation created: {conversation_key} for visitor: {visitor_key}")
        
        
    except Exception as e:
        print(f"Error handling conversation creation event: {e}")

# ---------------------------------------------------------------------------------------------------------------------------
# DONOT TOUCH-----------------------------------
#---------------------------------------------------------------------------------------------------------------------------
# WebSocket event handlers
@socketio.on('join')
def on_join(data):
    """Handle client joining a room"""
    visitor_id = data['visitor_id']
    join_room(visitor_id)
    print(f"Client joined room: {visitor_id}")

@socketio.on('disconnect')
def on_disconnect():
    """Handle client disconnect"""
    print('Client disconnected')


# ---------------------------------------------------------------------------------------------------------------------------
# DONOT TOUCH-----------------------------------
#---------------------------------------------------------------------------------------------------------------------------

@app.route('/api/start-chat', methods=['POST'])
def start_chat():
    """Initialize a new chat session"""
    try:
        visitor_id = str(uuid.uuid4()).replace('-', '')  
        print(f"Starting chat for visitor: {visitor_id}")
        
        # Stop existing session for same visitor if exists BEFORE starting new one
        if visitor_id in heygen_sessions:
            old_session = heygen_sessions[visitor_id]
            old_session_id = old_session.get('session_id')
            if old_session_id:
                try:
                    print(f"Stopping old HeyGen session for visitor: {visitor_id}")
                    heygen_client_temp = HeyGenStreamingClient(api_key=HEYGEN_API_KEY)
                    heygen_client_temp.stop_session(old_session_id)
                    print(f"Old session {old_session_id} stopped successfully")
                except Exception as e:
                    print(f"Error stopping old session: {e}")
                finally:
                    # Clean up old session data
                    del heygen_sessions[visitor_id]
        
        # Start conversation with WotNot
        conversation_data = wotnot_client.start_conversation(visitor_id)
        if not conversation_data:
            return jsonify({'success': False, 'error': 'Failed to start conversation with WotNot'}), 500
        
        thread_id = conversation_data.get('conversation', {}).get('id')
        if not thread_id:
            print(f"No thread_id found in response: {conversation_data}")
            return jsonify({'success': False, 'error': 'No thread_id received from WotNot'}), 500
        
        # Create mapping
        wotnot_to_local_mapping[str(thread_id)] = visitor_id
        print(f"Created mapping: {thread_id} -> {visitor_id}")
        
        conversation_threads[visitor_id] = {
            'thread_id': thread_id,
            'visitor_id': visitor_id,
            'created_at': datetime.now().isoformat(),
            'messages': []
        }
        
        # Extract initial message
        initial_message = None
        if 'messages' in conversation_data and conversation_data['messages']:
            for msg in conversation_data['messages']:
                if msg.get('from', {}).get('type') == 'BOT':
                    raw_message = msg.get('data', {}).get('body', '')
                    initial_message = strip_html_tags(raw_message)
                    break
        
        if initial_message:
            conversation_threads[visitor_id]['messages'].append({
                'type': 'bot',
                'message': initial_message,
                'timestamp': datetime.now().isoformat()
            })
        
        print(f"Chat started successfully for visitor: {visitor_id}")
        
        # --- HEYGEN SETUP STARTS HERE ---
        heygen_client = HeyGenStreamingClient(api_key=HEYGEN_API_KEY)
        print(f"HEYGEN_API_KEY: {HEYGEN_API_KEY}")
        
        # Create token
        token_data = heygen_client.create_token()
        if not token_data or 'token' not in token_data:
            raise Exception("Failed to generate HeyGen token")
        print(f"[create_token] Success: {token_data}")

        avatar_id = "Pedro_CasualLook_public"
        voice_id = "8f389c2237194f80b50fe7632dcc17b8"

        # Start streaming session
        session_data = heygen_client.start_streaming_session(avatar_id, voice_id)
        realtime_endpoint = session_data['data'].get('realtime_endpoint', '')

        if not session_data or 'data' not in session_data or 'session_id' not in session_data['data']:
            raise Exception("Failed to start HeyGen streaming session")
        
        print(f"[start_streaming_session] Success: {session_data}")

        session_id = session_data['data']['session_id']
        url = session_data['data'].get('url', '')
        access_token = session_data['data'].get('access_token', '')

        # Store new session
        heygen_sessions[visitor_id] = {
            'session_id': session_id,
            'token': access_token,
            'url': url,
            'avatar_id': avatar_id,
            'voice_id': voice_id,
            'started_at': datetime.now().isoformat(),
            'webrtc_started': False,
            'session_ready': False,
            'realtime_endpoint': realtime_endpoint
        }

        # Start WebRTC connection
        try:
            start_response = heygen_client.start_webrtc(session_id)
            print(f"[start_webrtc] Response: {start_response}")
            
            if start_response and start_response.get('code') == 100:
                heygen_sessions[visitor_id]['webrtc_started'] = True
                heygen_sessions[visitor_id]['session_ready'] = True
                print(f"WebRTC started successfully for session: {session_id}")
            else:
                print(f"WebRTC start failed: {start_response}")
                
        except Exception as e:
            print(f"Error starting WebRTC: {e}")
            # Don't fail the entire request, just log the error
            heygen_sessions[visitor_id]['webrtc_started'] = False
            heygen_sessions[visitor_id]['session_ready'] = False

        # Send initial message only if session is ready
        if initial_message and heygen_sessions[visitor_id].get('session_ready', False):
            try:
                # Add a small delay to ensure WebRTC is fully established
                import time
                time.sleep(1)
                
                task_response = heygen_client.send_text_task(session_id, initial_message)
                print(f"[send_text_task] Initial message response: {task_response}")
                
                if task_response and task_response.get('code') == 100:
                    print(f"Initial message sent successfully: {initial_message}")
                else:
                    print(f"Initial message send failed: {task_response}")
                    
            except Exception as e:
                print(f"Error sending initial message: {e}")
        
        return jsonify({
            'success': True,
            'visitor_id': visitor_id,
            'thread_id': thread_id,
            'initial_message': initial_message,
            'heygen': {
                'session_id': session_id,
                'access_token': access_token,
                'url': url,
                'realtime_endpoint': realtime_endpoint,
                'avatar_id': avatar_id,
                'voice_id': voice_id,
                'session_ready': heygen_sessions[visitor_id].get('session_ready', False)
            }
        })

    except Exception as e:
        print(f"Error in start_chat: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@app.route('/api/send-message', methods=['POST'])
def send_message():
    """Send user message and get bot response"""
    try:
        data = request.get_json()
        visitor_id = data.get('visitor_id')
        message = data.get('message')
        
        if not visitor_id or not message:
            return jsonify({
                'success': False,
                'error': 'Missing visitor_id or message'
            }), 400
        
        conversation = conversation_threads.get(visitor_id)
        if not conversation:
            return jsonify({
                'success': False,
                'error': 'Conversation not found'
            }), 404
        
        thread_id = conversation['thread_id']
        
        # Store user message
        conversation['messages'].append({
            'type': 'user',
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
        
        print(f"Sending message for visitor {visitor_id}: {message}")
        
        # Send message to WotNot
        response_data = wotnot_client.send_visitor_message(thread_id, message, visitor_id)
        
        if not response_data:
            return jsonify({
                'success': False,
                'error': 'Failed to send message to WotNot'
            }), 500
        
        # Bot responses will come via webhook
        return jsonify({
            'success': True,
            'message': 'Message sent successfully',
            'message_id': response_data.get('id') or response_data.get('message_id')
        })
        
    except Exception as e:
        print(f"Error in send_message: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@app.route('/api/stop-chat', methods=['POST'])
def stop_chat():
    """Stop chat session and cleanup resources"""
    try:
        # Handle both JSON and form data
        if request.content_type == 'application/json':
            data = request.get_json()
        else:
            # Handle sendBeacon with text/plain content type
            try:
                data = json.loads(request.data.decode('utf-8'))
            except:
                data = request.form.to_dict()
        
        visitor_id = data.get("visitor_id")
        
        if not visitor_id:
            return jsonify({"success": False, "error": "Missing visitor_id"}), 400
        
        # Stop HeyGen session if exists
        if visitor_id in heygen_sessions:
            session_info = heygen_sessions[visitor_id]
            session_id = session_info.get('session_id')
            
            if session_id:
                try:
                    heygen_client = HeyGenStreamingClient(api_key=HEYGEN_API_KEY)
                    stop_response = heygen_client.stop_session(session_id)
                    print(f"[stop_session] Response: {stop_response}")
                    print(f"Stopped HeyGen session for visitor: {visitor_id}")
                except Exception as e:
                    print(f"Error stopping HeyGen session: {e}")
                finally:
                    # Always clean up the session data
                    del heygen_sessions[visitor_id]
        
        # Clean up conversation threads
        if visitor_id in conversation_threads:
            thread_id = conversation_threads[visitor_id].get('thread_id')
            del conversation_threads[visitor_id]
            
            # Clean up mapping
            if thread_id and str(thread_id) in wotnot_to_local_mapping:
                del wotnot_to_local_mapping[str(thread_id)]
        
        return jsonify({"success": True, "message": "Chat session stopped successfully"})
    
    except Exception as e:
        print(f"Error in stop_chat: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": "Server error"}), 500

@app.route('/webhook/wotnot', methods=['POST'])
def wotnot_webhook():
    """Handle incoming WotNot webhook events"""
    try:
        data = request.get_json()
        
        token = None
        if data:
            token = data.get('token')
        
        if not token:
            token = request.headers.get('Authorization')
        
        # Handle webhook verification request
        if data and 'token' in data and not data.get('events'):
            print("Webhook verification request received")
            return jsonify({'token': data['token']}), 200
        
        # Validate webhook token
        if token != WEBHOOK_TOKEN:
            print(f"Invalid webhook token received: {token}")
            return jsonify({'error': 'Invalid token'}), 401
        
        # Process events
        if data and 'events' in data:
            for event_data in data['events']:
                handle_wotnot_event(event_data)
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        print(f"Error handling webhook: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal server error'}), 500

def handle_wotnot_event(event_data):
    """Process individual WotNot events"""
    try:
        event = event_data.get('event', {})
        event_type = event.get('type')
        
        print(f"Processing event type: {event_type}")
        
        if event_type == 'message':
            handle_message_event(event_data)
        elif event_type == 'conversation_create':
            handle_conversation_creation_event(event_data)
        
    except Exception as e:
        print(f"Error processing event: {e}")
        import traceback
        traceback.print_exc()

def handle_message_event(event_data):
    """Handle message exchange events with HeyGen integration"""
    try:
        event = event_data.get('event', {})
        payload = event.get('payload', {})
        message = payload.get('message', {})
        message_by = payload.get('message_by', {})
        
        conversation = event_data.get('conversation', {})
        
        conversation_key = str(conversation.get('key'))
        message_text = message.get('text', '')
        message_type = message_by.get('type', '')
        
        print(f"Message event - Conversation: {conversation_key}, Type: {message_type}, Text: {message_text}")
        
        # Get local visitor ID from mapping
        local_visitor_id = wotnot_to_local_mapping.get(conversation_key)
        
        if local_visitor_id and local_visitor_id in conversation_threads:
            
            # Skip visitor messages
            if message_type == 'visitor':
                print(f"Skipping visitor message for conversation {conversation_key}")
                return
           
            # Process bot messages
            if message_type == 'bot':
                clean_text = None
                message_data = None
                
                # Handle text messages
                if message.get('type') == 'text':
                    clean_text = strip_html_tags(message_text)
                    if clean_text and clean_text.strip():
                        message_data = {
                            'type': 'bot',
                            'message': clean_text,
                            'timestamp': datetime.now().isoformat(),
                            'source': 'webhook'
                        }
                        print(f"Bot text message processed for conversation {local_visitor_id}")
                
                # Handle button messages
                elif message.get('type') == 'button':
                    button_payload = message.get('payload', {})
                    title = strip_html_tags(button_payload.get('title', ''))
                    buttons = button_payload.get('buttons', [])
                    
                    if title and title.strip():
                        clean_text = title  # Use title as the text to send to HeyGen
                        message_data = {
                            'type': 'bot',
                            'message': title,
                            'timestamp': datetime.now().isoformat(),
                            'source': 'webhook',
                            'buttons': [{'title': btn.get('title', ''), 'type': btn.get('type', '')} for btn in buttons]
                        }
                        print(f"Bot button message processed for conversation {local_visitor_id}")
                
                # If we have valid message data, store it and process
                if message_data and clean_text:
                    # Store message in conversation thread
                    conversation_threads[local_visitor_id]['messages'].append(message_data)
                    
                    # Send to HeyGen avatar if session exists and is ready
                    if local_visitor_id in heygen_sessions:
                        send_message_to_heygen(local_visitor_id, clean_text)
                    
                    # Emit to frontend via SocketIO
                    socketio.emit('new_message', {
                        'visitor_id': local_visitor_id,
                        'message': message_data
                    }, room=local_visitor_id)
                    
                else:
                    print("Message is empty after cleaning or processing")
                    
        else:
            print(f"No local conversation found for thread_id: {conversation_key}")
            print(f"Available mappings: {wotnot_to_local_mapping}")
            
    except Exception as e:
        print(f"Error handling message event: {e}")
        import traceback
        traceback.print_exc()

def send_message_to_heygen(visitor_id, message_text):
    """Send message to HeyGen avatar"""
    try:
        session_info = heygen_sessions[visitor_id]
        session_id = session_info.get('session_id')
        
        if not session_id:
            print(f"No HeyGen session_id found for visitor: {visitor_id}")
            return
        
        heygen_client = HeyGenStreamingClient(api_key=HEYGEN_API_KEY)
        
        # Check if session is ready
        if session_info.get('session_ready', False):
            # Session is ready, send the message directly
            task_response = heygen_client.send_text_task(session_id, message_text)
            print(f"HeyGen task response status: {task_response.get('code') if task_response else 'None'}")
            print(f"HeyGen task response: {task_response}")
            
            if not (task_response and task_response.get('code') == 100):
                print(f"HeyGen task failed: {task_response}")
                
        else:
            # Session not ready, try to start WebRTC first
            print(f"HeyGen session not ready for visitor: {visitor_id}")
            
            if not session_info.get('webrtc_started', False):
                # Start WebRTC
                start_response = heygen_client.start_webrtc(session_id)
                print(f"[start_webrtc] Status: {start_response.get('code') if start_response else 'None'}")
                print(f"[start_webrtc] Response: {start_response}")
                
                if start_response and start_response.get('code') == 100:
                    # WebRTC started successfully
                    heygen_sessions[visitor_id]['webrtc_started'] = True
                    heygen_sessions[visitor_id]['session_ready'] = True
                    print(f"HeyGen WebRTC started successfully for visitor: {visitor_id}")
                    
                    # Now send the message
                    task_response = heygen_client.send_text_task(session_id, message_text)
                    print(f"HeyGen task response status: {task_response.get('code') if task_response else 'None'}")
                    print(f"HeyGen task response: {task_response}")
                    
                    if not (task_response and task_response.get('code') == 100):
                        print(f"HeyGen task failed after WebRTC start: {task_response}")
                        
                else:
                    print(f"Failed to start WebRTC: {start_response}")
            else:
                print(f"WebRTC already started but session not ready for visitor: {visitor_id}")
                
    except Exception as e:
        print(f"Error sending message to HeyGen avatar: {e}")
        import traceback
        traceback.print_exc()

def handle_conversation_creation_event(event_data):
    """Handle conversation creation events"""
    try:
        conversation = event_data.get('conversation', {})
        visitor = event_data.get('visitor', {})
        
        conversation_key = str(conversation.get('key'))
        visitor_key = visitor.get('key')
        
        print(f"New conversation created: {conversation_key} for visitor: {visitor_key}")
        
    except Exception as e:
        print(f"Error handling conversation creation event: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)