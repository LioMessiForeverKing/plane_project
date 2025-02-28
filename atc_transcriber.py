import requests
import subprocess
import io
import wave
import speech_recognition as sr

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
        pls_url = "https://www.liveatc.net/play/ksfo_gnd.pls"
        print("Fetching stream URL...")
        stream_url = get_stream_url(pls_url)
        print("Streaming from:", stream_url)

        # Step 2: Start FFmpeg to capture the audio stream
        ffmpeg_command = [
            "ffmpeg",
            "-i", stream_url,
            "-f", "s16le",           # output raw 16-bit PCM data
            "-acodec", "pcm_s16le",
            "-ar", "16000",          # set sample rate to 16000 Hz
            "-ac", "1",              # mono audio
            "-loglevel", "quiet",    # suppress extra output
            "pipe:1"
        ]

        process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE)

        # Step 3: Set up the speech recognizer
        recognizer = sr.Recognizer()
        SAMPLE_RATE = 16000
        CHUNK_DURATION = 10  # seconds
        SAMPLES_PER_CHUNK = CHUNK_DURATION * SAMPLE_RATE
        BYTES_PER_SAMPLE = 2  # 16-bit PCM -> 2 bytes per sample

        print("Starting transcription...")
        while True:
            # Read enough bytes for one chunk of audio
            raw_audio = process.stdout.read(SAMPLES_PER_CHUNK * BYTES_PER_SAMPLE)
            if not raw_audio:
                break  # stream ended

            # Wrap the raw audio in a WAV container in memory
            audio_stream = io.BytesIO()
            with wave.open(audio_stream, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(BYTES_PER_SAMPLE)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(raw_audio)
            audio_stream.seek(0)

            # Use SpeechRecognition to transcribe the audio chunk
            with sr.AudioFile(audio_stream) as source:
                audio_data = recognizer.record(source)
            try:
                transcription = recognizer.recognize_google(audio_data)
                print("Transcription:", transcription)
            except sr.UnknownValueError:
                print("Google Speech Recognition could not understand audio")
            except sr.RequestError as e:
                print("Could not request results from Google Speech Recognition service; {0}".format(e))

    except KeyboardInterrupt:
        print("\nStopping transcription...")
        if 'process' in locals():
            process.terminate()
    except Exception as e:
        print(f"An error occurred: {e}")
        if 'process' in locals():
            process.terminate()

if __name__ == "__main__":
    main()