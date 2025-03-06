Engineered a real-time ATC transcription system for KSFO ground control by capturing live audio from LiveATC.net and converting MP3 streams to 16kHz, 16-bit linear PCM using FFmpeg.
Leveraged Deepgram's nova-2-atc model to transcribe audio in real time by processing 4096-byte chunks via WebSocket connections, ensuring low-latency and high accuracy.
Integrated Google Gemini AI (v2.0-flash) to post-process raw transcriptions, enhancing readability and clarity for complex ATC communications.
Implemented an asynchronous communication architecture using Python’s asyncio, threading, and a producer-consumer Queue, enabling real-time broadcast over a WebSocket server on localhost:8765 with robust shutdown mechanisms.
