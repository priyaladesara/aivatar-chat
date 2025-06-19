# Real-Time AI Chatbot with Avatar

This project is a web-based chatbot interface that allows users to have real-time conversations with an AI, enhanced by a speaking video avatar.

## Project Overview

The goal of this project is to create a more engaging and human-like chat experience. Instead of just displaying text responses, the bot replies are also spoken by an animated avatar, making the interaction feel more personal and lifelike.

## Key Features

- Real-time chat interface
- AI-powered responses
- Video avatar that speaks each bot reply
- Fast audio and video streaming for instant playback
- Works on both desktop and mobile devices

## How It Works

1. When a user starts the chat, a new session is created.
2. The user’s message is sent to the AI chatbot engine.
3. The bot's response is processed and converted into spoken video by an avatar service.
4. The video and audio are streamed directly to the browser in real time.
5. The chat continues interactively with both text and avatar-based responses.

   
 ![AIVATAR-CHAT drawio](https://github.com/user-attachments/assets/cff67f28-d6ce-44b9-b275-ae4e954d92a9)


## Technologies Used

- HTML, CSS, JavaScript for the frontend
- Flask for the backend API handling
- Socket.IO and WebSocket for real-time communication
- LiveKit and HeyGen for video/audio streaming and avatar generation

## Possible Use Cases

- Virtual support assistants
- AI onboarding bots
- Educational chat systems
- Interactive product walkthroughs

## Notes

This project demonstrates the integration of conversational AI with real-time video rendering to create a more immersive user experience. It is designed as a prototype to explore the potential of AI avatars in customer-facing applications.

