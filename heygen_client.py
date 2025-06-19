import requests

class HeyGenStreamingClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.heygen.com"
        self.headers = {
            "x-api-key": self.api_key,
            "accept": "application/json",
            "content-type": "application/json"
        }

    def create_token(self):
        """Generate a new access token for a HeyGen streaming session.
        This token is required to start a unique streaming session."""
        url = f"{self.base_url}/v1/streaming.create_token"
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "x-api-key": self.api_key
        }

        try:
            response = requests.post(url, json={}, headers=headers)
            print(f"[create_token] Status: {response.status_code}")
            print(f"[create_token] Response: {response.text}")
            response.raise_for_status()
            json_data = response.json()
            return json_data.get("data", {})  # <-- FIX
        except requests.exceptions.RequestException as e:
            print(f"[create_token] Error: {e}")
            print(f"[create_token] Response content: {response.text if 'response' in locals() else 'No response'}")
            return None

    def list_streaming_avatars(self):
        """List available streaming avatars"""
        url = f"{self.base_url}/v1/streaming/avatar.list"

        headers = {
            "accept": "application/json",
            "x-api-key": self.api_key
        }

        try:
            response = requests.get(url, headers=headers)
            print(f"[list_streaming_avatars] Status: {response.status_code}")
            print(f"[list_streaming_avatars] Response: {response.text}")

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[list_streaming_avatars] Error: {e}")
            print(f"[list_streaming_avatars] Response content: {response.text if 'response' in locals() else 'No response'}")
            return None

    def start_streaming_session(self, avatar_id, voice_id):
        """
        Initiate a new streaming session with HeyGen's Interactive Avatar API.
        Returns session_id, websocket URL, access_token, and other metadata.
        """
        url = f"{self.base_url}/v1/streaming.new"

        payload = {
            "avatar_id": avatar_id,
            "voice_id": voice_id,
            "quality": "medium",
            "voice": {
                "rate": 1
            },
            "video_encoding": "VP8",
            "disable_idle_timeout": False,
            "version": "v2",
            "stt_settings": {
                "provider": "deepgram",
                "confidence": 0.55
            },
            "activity_idle_timeout": 120
        }

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "x-api-key": self.api_key
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            print(f"[start_streaming_session] Status: {response.status_code}")
            print(f"[start_streaming_session] Response: {response.text}")

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[start_streaming_session] Error: {e}")
            print(f"[start_streaming_session] Response content: {response.text if 'response' in locals() else 'No response'}")
            return None

    def start_webrtc(self, session_id):
        """
        Starts an existing HeyGen streaming session.
        Establishes connection between the client and avatar.

        Args:
            session_id (str): The session ID to start.

        Returns:
            dict: JSON response from HeyGen API.
        """
        url = f"{self.base_url}/v1/streaming.start"

        payload = {
            "session_id": session_id
        }

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "x-api-key": self.api_key
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            print(f"[start_webrtc] Status: {response.status_code}")
            print(f"[start_webrtc] Response: {response.text}")

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[start_webrtc] Error: {e}")
            print(f"[start_webrtc] Response content: {response.text if 'response' in locals() else 'No response'}")
            return None

    def send_text_task(self, session_id, text, task_mode="sync", task_type="repeat"):
        """
        Send a text task to the streaming avatar session.
        
        Parameters:
        - session_id: ID of the active streaming session.
        - text: The text the avatar should speak.
        - task_mode: "sync" or "async" (default is "sync").
        - task_type: "repeat" or "chat" (default is "repeat").
        
        Returns:
        - JSON response with task_id and duration_ms
        """
        url = f"{self.base_url}/v1/streaming.task"
        payload = {
            "session_id": session_id,
            "text": text,
            "task_mode": task_mode,
            "task_type": task_type
        }

        try:
            response = requests.post(url, headers=self.headers, json=payload)
            print(f"HeyGen task response status: {response.status_code}")
            print(f"HeyGen task response: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error sending text task: {e}")
            print(f"Response content: {response.text if 'response' in locals() else 'No response'}")
            return None
            
    def stop_session(self, session_id):
        """
        Stop or terminate an active streaming session.

        Parameters:
        - session_id: ID of the session to be terminated.

        Returns:
        - JSON response containing the status ("success" if stopped successfully).
        """
        url = f"{self.base_url}/v1/streaming.stop"
        payload = {
            "session_id": session_id
        }

        try:
            response = requests.post(url, headers=self.headers, json=payload)
            print(f"HeyGen stop session response status: {response.status_code}")
            print(f"HeyGen stop session response: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error stopping session: {e}")
            print(f"Response content: {response.text if 'response' in locals() else 'No response'}")
            return None