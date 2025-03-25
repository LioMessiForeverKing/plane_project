# Real-Time Aviation Tracking System

Live map visualization of aircraft around SFO with real-time ATC transcription integration using ADS-B data and AI speech recognition.

## Features
- 🛫 Live aircraft tracking with position, altitude, and heading
- 🎧 Real-time ATC communications transcription
- ✈️ Interactive Leaflet.js map with aircraft icons
- 🔁 Automatic data updates every 5 seconds
- 🤖 AI-enhanced transcription clarity using Gemini

## Installation
```bash
pip install -r requirements.txt
```

## Configuration
1. Obtain API keys:
   - [ADSB Exchange](https://www.adsbexchange.com/)
   - [Deepgram](https://deepgram.com/)
2. Create `.env` file:
```env
ADSBLIVE_API_KEY=your_adsb_exchange_key
DEEPGRAM_API_KEY=your_deepgram_key
```

## Usage
1. Start backend services:
```bash
python atc_transcriber.py
```
2. Open `map.html` in browser
3. Aircraft positions update automatically
4. Live transcriptions appear in overlay

⚠️ Note: Flight data updates automatically stop after 30 seconds for API conservation. Restart the page to refresh.

## API Requirements
- ADSB Exchange API for live flight data
- Deepgram Nova-2-ATC model for speech recognition
- WebSocket server on port 8765
