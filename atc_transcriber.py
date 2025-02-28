import requests
import threading
import subprocess
import os
from dotenv import load_dotenv
from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
)

# Load environment variables
load_dotenv()

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

def main():
    try:
        # Initialize Deepgram client with API key
        api_key = os.getenv('DEEPGRAM_API_KEY')
        if not api_key:
            raise Exception("DEEPGRAM_API_KEY not found in environment variables")
        deepgram = DeepgramClient(api_key)
        
        # Create a websocket connection to Deepgram
        dg_connection = deepgram.listen.websocket.v("1")

        # Define the transcription callback
        def on_message(self, result, **kwargs):
            sentence = result.channel.alternatives[0].transcript
            if not sentence:
                return
            print(f"ATC: {sentence}")

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
        input("Press Enter to stop transcription...\n")

        # Signal the streaming thread to exit
        lock_exit.acquire()
        exit_flag = True
        lock_exit.release()

        stream_worker.join()

        # Close the Deepgram connection
        dg_connection.finish()
        print("Transcription stopped")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
