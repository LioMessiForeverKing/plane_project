import requests
import threading
import subprocess
import os
import time
from queue import Queue
from dotenv import load_dotenv
from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
)
from websockets.server import serve
import asyncio
import json
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Initialize Gemini AI
genai.configure(api_key="AIzaSyA_iyHWfwE4E0MzNCuQ4C0cIzFkdDJ8sc8")
model = genai.GenerativeModel('gemini-2.0-flash')

# Initialize message queue
message_queue = Queue()

# Global WebSocket clients set
websocket_clients = set()

# WebSocket handler
async def handle_client(websocket):
    websocket_clients.add(websocket)
    try:
        async for message in websocket:
            pass  # We don't expect messages from the client
    finally:
        websocket_clients.remove(websocket)

# Function to broadcast transcription to all connected clients
async def broadcast_transcription(text):
    if websocket_clients:  # Only attempt to broadcast if there are connected clients
        message = json.dumps({"transcription": text})
        await asyncio.gather(
            *[client.send(message) for client in websocket_clients]
        )

# Step 1: Download and parse the PLS file to get the stream URL
def get_stream_url(pls_url):
    response = requests.get(pls_url)
    if response.status_code != 200:
        raise Exception("Could not retrieve PLS file")
    lines = response.text.splitlines()
    for line in lines:
        if line.startswith("File1="):
            return line.split("=", 1)[1].strip()
    raise Exception("No stream URL found in PLS file")

# Define the transcription callback outside of main
async def process_queue():
    while True:
        if not message_queue.empty():
            raw_text = message_queue.get()
            try:
                # Process the text through Gemini AI
                prompt = f"Format this ATC communication in a clear, readable way. your output should not be more than one line: {raw_text}"
                response = model.generate_content(prompt)
                formatted_text = response.text
                print(f"Original ATC: {raw_text}")
                print(f"Formatted ATC: {formatted_text}")
                
                # Broadcast the formatted text
                await broadcast_transcription(formatted_text)
            except Exception as e:
                print(f"Error processing message through Gemini: {e}")
                # Fallback to original text if Gemini processing fails
                await broadcast_transcription(raw_text)
        await asyncio.sleep(0.1)

def on_message(self, result, **kwargs):
    sentence = result.channel.alternatives[0].transcript
    if not sentence:
        return
    # Add the message to the queue instead of broadcasting directly
    message_queue.put(sentence)

async def main():
    try:
        # Start WebSocket server
        websocket_server = await serve(handle_client, "localhost", 8765)
        print("WebSocket server started on ws://localhost:8765")

        # Start the queue processor
        asyncio.create_task(process_queue())

        # Initialize Deepgram client with API key
        api_key = os.getenv('DEEPGRAM_API_KEY')
        if not api_key:
            raise Exception("DEEPGRAM_API_KEY not found in environment variables")
        deepgram = DeepgramClient(api_key)
        
        # Create a websocket connection to Deepgram
        dg_connection = deepgram.listen.websocket.v("1")

        # Set up the message handler
        dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)

        # Get the stream URL from PLS file
        pls_url = "https://www.liveatc.net/play/ksfo_gnd.pls"
        print("Fetching stream URL...")
        stream_url = get_stream_url(pls_url)
        print("Streaming from:", stream_url)

        # Configure Deepgram options for linear16 PCM audio
        options = LiveOptions(
            model="nova-2-atc",
            smart_format=True,
            language="en",
            encoding="linear16",
            channels=1,
            sample_rate=16000
        )

        print("\nStarting transcription... Press Enter to stop.\n")
        
        # Start the Deepgram connection
        if not dg_connection.start(options):
            print("Failed to start Deepgram connection")
            return

        # Set up thread control for a clean shutdown
        lock_exit = threading.Lock()
        exit_flag = False

        # Launch FFmpeg to convert the MP3 stream to linear16 PCM audio
        ffmpeg_command = [
            "ffmpeg",
            "-i", stream_url,
            "-f", "s16le",            # output raw PCM data
            "-acodec", "pcm_s16le",
            "-ar", "16000",           # sample rate of 16kHz
            "-ac", "1",               # mono audio
            "-loglevel", "quiet",     # suppress FFmpeg output
            "pipe:1"                  # pipe to stdout
        ]
        ffmpeg_process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE)

        # Define the streaming thread that reads from FFmpeg and sends data to Deepgram
        def stream_thread():
            try:
                while True:
                    lock_exit.acquire()
                    if exit_flag:
                        lock_exit.release()
                        break
                    lock_exit.release()

                    # Read a small chunk of data from FFmpeg's stdout
                    data = ffmpeg_process.stdout.read(4096)
                    if not data:
                        break
                    # Send the chunk of PCM data to Deepgram
                    dg_connection.send(data)
            except Exception as e:
                print(f"Streaming error: {e}")
            finally:
                ffmpeg_process.terminate()

        # Start the streaming thread
        stream_worker = threading.Thread(target=stream_thread)
        stream_worker.start()

        # Wait for user input to stop transcription
        await asyncio.get_event_loop().run_in_executor(None, input, "Press Enter to stop transcription...\n")

        # Signal the streaming thread to exit
        lock_exit.acquire()
        exit_flag = True
        lock_exit.release()

        stream_worker.join()

        # Close the Deepgram connection and WebSocket server
        dg_connection.finish()
        websocket_server.close()
        await websocket_server.wait_closed()
        print("Transcription stopped")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
