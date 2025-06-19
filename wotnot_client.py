import requests
import re

class WotNotAPI:
    def __init__(self, api_key, bot_key, base_url):
        self.api_key = api_key
        self.bot_key = self.clean_publish_key(bot_key)
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    
    def clean_publish_key(self, key):
        """Clean publish key by removing special characters, emojis, and whitespace"""
        key = key.strip()
        key = re.sub(r'[^a-zA-Z0-9]', '', key)
        return key
    
    def start_conversation(self, visitor_id, initial_message="Hello"):
        """Start a new conversation with WotNot"""
        url = f"{self.base_url}/conversations"  
        
        clean_visitor_id = self.clean_publish_key(visitor_id)
        
        payload = {
            "channel": "API",
            "message": {
                "data": {
                    "body": initial_message
                },
                "type": "text"
            },
            "variables": {
                "system": { 
                    "timezone": "Asia/Calcutta",
                    "referrerUrl": "https://wotnot.io",
                    "browserLanguage": "en-GB"
                }
            },
            "publish_key": self.bot_key,
            "from": {
                "user_external_id": clean_visitor_id,
                "type": "VISITOR"
            }
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.text}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error starting conversation: {e}")
            print(f"Response content: {response.text if 'response' in locals() else 'No response'}")
            return None
    
    def send_visitor_message(self, thread_id, message, visitor_id):
        """Send visitor message to WotNot"""
        url = f"{self.base_url}/conversation/{thread_id}/messages"
        
        payload = {
            "message": {
                "data": {
                    "body": message
                },
                "type": "text"
            },
            "user": {
                "type": "VISITOR"
            }
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            print(f"Message response status: {response.status_code}")
            print(f"Message response content: {response.text}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error sending message: {e}")
            print(f"Response content: {response.text if 'response' in locals() else 'No response'}")
            return None