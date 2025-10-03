import os
import asyncio
import json
import base64
import sounddevice as sd
import numpy as np
import websockets
from threading import Thread, Event
import ssl
import certifi

# Audio settings - Realtime API requires 24kHz, 16-bit PCM, mono
SAMPLE_RATE = 24000
CHANNELS = 1
DTYPE = np.int16

class RealtimeClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.ws = None
        self.is_recording = False
        self.is_playing = False
        self.recording_stream = None
        self.stop_recording = Event()
        
    async def connect(self):
        """Establish WebSocket connection to OpenAI Realtime API"""
        url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "OpenAI-Beta": "realtime=v1"
        }
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        print("Connecting to OpenAI Realtime API...")
        self.ws = await websockets.connect(url, additional_headers=headers, ssl=ssl_context)
        print("Connected!")
        
        # Configure the session
        await self.ws.send(json.dumps({
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": "You are a helpful tutor assistant. Be concise and clear.",
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": None  # We'll manually control turns
            }
        }))
        
    async def send_audio_chunk(self, audio_data):
        """Send audio chunk to the API"""
        # Convert numpy array to bytes, then base64
        audio_bytes = audio_data.tobytes()
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        await self.ws.send(json.dumps({
            "type": "input_audio_buffer.append",
            "audio": audio_base64
        }))
    
    async def commit_audio(self):
        """Tell the API we're done sending audio and want a response"""
        print("Committing audio buffer...")
        await self.ws.send(json.dumps({
            "type": "input_audio_buffer.commit"
        }))
        
        # Create a response
        await self.ws.send(json.dumps({
            "type": "response.create"
        }))
    
    def audio_callback(self, indata, frames, time_info, status):
        """Callback for recording audio"""
        if status:
            print(f"Recording status: {status}")
        
        # Queue the audio to be sent
        if self.is_recording and self.ws:
            # We'll send this in the async loop
            asyncio.run_coroutine_threadsafe(
                self.send_audio_chunk(indata.copy()),
                self.loop
            )
    
    async def start_recording(self):
        """Start recording audio from microphone"""
        print("\nRecording... Press Enter to stop and get response.")
        self.is_recording = True
        self.stop_recording.clear()
        
        # Start audio input stream
        self.recording_stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            callback=self.audio_callback
        )
        self.recording_stream.start()
        
        # Wait for user to press Enter
        await asyncio.get_event_loop().run_in_executor(
            None, 
            input
        )
        
        # Stop recording
        self.is_recording = False
        self.recording_stream.stop()
        self.recording_stream.close()
        print("Recording stopped.")
        
        # Commit the audio buffer to get response
        await self.commit_audio()
    
    async def handle_messages(self):
        """Listen for messages from the API"""
        audio_chunks = []
        
        try:
            async for message in self.ws:
                data = json.loads(message)
                msg_type = data.get("type")
                
                # Print important events
                if msg_type == "session.created":
                    print("Session created")
                elif msg_type == "session.updated":
                    print("Session configured")
                elif msg_type == "input_audio_buffer.speech_started":
                    print("Speech detected")
                elif msg_type == "input_audio_buffer.committed":
                    print("Audio buffer committed")
                elif msg_type == "response.audio_transcript.delta":
                    # Print transcript as it comes in
                    print(data.get("delta", ""), end="", flush=True)
                elif msg_type == "response.audio.delta":
                    # Collect audio chunks
                    audio_base64 = data.get("delta", "")
                    if audio_base64:
                        audio_bytes = base64.b64decode(audio_base64)
                        audio_array = np.frombuffer(audio_bytes, dtype=DTYPE)
                        audio_chunks.append(audio_array)
                elif msg_type == "response.audio.done":
                    print("\n\nPlaying response...")
                    # Play all collected audio
                    if audio_chunks:
                        full_audio = np.concatenate(audio_chunks)
                        sd.play(full_audio, SAMPLE_RATE)
                        sd.wait()
                        print("Response complete.\n")
                    audio_chunks = []
                elif msg_type == "response.done":
                    print("Ready for next question.")
                elif msg_type == "error":
                    print(f"Error: {data}")
                    
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed")
    
    async def run(self):
        """Main run loop"""
        self.loop = asyncio.get_event_loop()
        
        await self.connect()
        
        # Start listening for messages in background
        message_task = asyncio.create_task(self.handle_messages())
        
        try:
            while True:
                print("\nPress Enter to start recording...")
                await asyncio.get_event_loop().run_in_executor(None, input)
                
                await self.start_recording()
                
                # Give some time for response to complete
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            if self.recording_stream:
                self.recording_stream.stop()
                self.recording_stream.close()
            if self.ws:
                await self.ws.close()
            message_task.cancel()

async def main():
    # Get API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        config_path = os.path.expanduser('~/.tutor_openai')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                api_key = f.read().strip()
        else:
            print("Error: OPENAI_API_KEY not found")
            return
    
    client = RealtimeClient(api_key)
    await client.run()

if __name__ == "__main__":
    print("OpenAI Realtime API Test")
    print("=" * 40)
    asyncio.run(main())