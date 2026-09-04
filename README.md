# 🪐 IGIRS AI 0.1 — 3D Cyber Command Center

> **An advanced, zero-dependency 3D desktop companion powered by NVIDIA NIM, WebGL, Edge-TTS Neural Voice, and Real-Time Screen Vision.**

![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-brightgreen.svg)
![NVIDIA NIM](https://img.shields.io/badge/LLM-Meta--Llama--3.2--11B--Vision-76B900.svg)
![Voice](https://img.shields.io/badge/TTS-Edge--TTS%20Neural-purple.svg)
![Platform](https://img.shields.io/badge/platform-Windows-0078D6.svg)

---

## 🌟 Highlights & Features

### 1. 🪐 3D Liquid Plasma Core & Gyroscopic Tech Rings
- **Native WebGL 3D Core**: Built with custom GLSL shaders with zero heavy external 3D dependencies.
- **Harmonic Fluid Displacement**: Organic multi-octave wave vertex shaders that morph the orb into living liquid energy.
- **Triple Concentric Gyroscopic Rings**: Tilted gimbal rings rotating along independent 3D axes with orbiting satellite nodes.
- **Acoustic Audio Waveform Equator**: A 96-line circular equalizer encircling the orb that erupts into dynamic bouncing audio waveform peaks when speaking.
- **Dynamic State Morphing**: Automatically switches color and animation tempo across states:
  - 🔵 **Standby**: Cyber Blue (`#3a86ff`) with serene celestial rotation.
  - 💠 **Listening**: Electric Cyan (`#00f0ff`) with expanding rings.
  - 🔴 **Thinking**: Flame Neon Rose (`#ff006e`) with high-speed gyroscopic precession.
  - 🟣 **Speaking**: Void Purple (`#8338ec`) with acoustic liquid ripples.

### 2. ⚡ Lightning-Fast Sub-Second Answers (<1s)
- **Tight Token Budgeting**: Capped completion tokens for rapid inference times (~1.0s) via NVIDIA NIM.
- **Direct First-Sentence Answers**: Delivers direct answers immediately in the very first sentence, cutting out robotic throat-clearing and filler preambles.
- **Smart Tool Routing**: Simple conversational chit-chat bypasses the function-calling engine entirely for instantaneous response times.

### 3. 🗣️ Natural Human Companion Voice
- **Neural Voice**: Powered by Microsoft Edge-TTS with `en-US-ChristopherNeural` (natural, confident, conversational JARVIS-like companion).
- **Conversational Pace**: Tuned to `+14%` rate for brisk, natural human pacing.
- **Human Phrasing**: Speaks with natural contractions (*"I'll"*, *"you're"*, *"here's"*, *"it's"*, *"don't"*, *"let's"*).

### 4. 🎙️ Hands-Free "Always Listening" Mode
- Toggle between Push-to-Talk and continuous hands-free voice chat.
- **Voice-Command Stop**: Simply say *"stop listen"*, *"stop listening"*, or *"mute mic"* to immediately exit continuous listening and return to standby.
- **Room Echo Protection**: Intelligent acoustic pause prevents the microphone from catching speaker audio.

### 5. 🎵 Direct YouTube Song Autoplay
- Resolves search queries to direct playable video IDs without requiring heavy official YouTube APIs or browser automation.
- Directly launches `https://www.youtube.com/watch?v={videoId}&autoplay=1` so your music starts playing immediately.

### 6. 👁️ Real-Time Screen Vision
- Instant screen grabbing and multi-modal scene analysis via NVIDIA NIM LLaMA-3.2-11B Vision.
- Ask questions like *"What is on my screen?"* or *"Debug this code on my screen"*.

### 7. 📊 Live System Telemetry & HUD Gauges
- Real-time CPU, RAM, and Battery power gauges with plugged-in battery detection.

### 8. 🧠 Persistent Fact Vault Memory
- Remembers user identity, preferences, and facts persistently across restarts in `facts_store.json`.

### 9. 📚 Knowledge Vault & Document RAG (Phase 5)
- Ingest and chat with local PDFs, Word `.docx`, Markdown, text notes, and code files.
- Local high-speed semantic retrieval and citation tracking without uploading files to external clouds.

### 10. 📱 Hands-Free WhatsApp & Email Assistant (Phase 6)
- **WhatsApp Desktop Automation**: Direct hands-free dispatch to contacts and phone numbers with dual-dispatch click & keystroke simulation.
- **Email Intelligence**: Native SMTP/IMAP client with AI email drafting and unread inbox checking.
- **Contacts Manager**: Manage phone numbers, emails, and nicknames directly via voice or GUI.

### 11. 🌐 Web Automation & Live Price Radar (Phase 8)
- **Live E-Commerce Price Radar**: Compares prices live across **Amazon.in** and **Flipkart**, detects best deals, computes savings differences, and provides audio briefings.
- **Smart Web Scraper**: Strips ads and boilerplate to extract clean markdown, data tables, and hyperlinks.
- **Visual Web Capture**: Headless browser webpage screenshot capturing with viewport and full-page support.

---

## 📂 Project Architecture

```
IGIRS AI/
├── run_desktop.py          # Main desktop launcher (3D Cyber Command Center)
├── assistant.py            # Central Assistant orchestrator & single-turn routing
├── config.py               # Global settings, voices, models, and directory configs
├── gui/
│   ├── api_bridge.py       # Python-JavaScript Bridge API
│   └── web/
│       └── index.html      # Glassmorphic HUD + WebGL 3D Orb + Comm, Docs & Web Tabs
├── llm/
│   ├── nvidia_client.py    # NVIDIA NIM client with auto key-rotation & fallback
│   └── prompts.py          # System prompt & human companion persona
├── tts/
│   ├── synthesizer.py      # Edge-TTS synthesizer with pyttsx3 fallback
│   ├── player.py           # Pygame non-blocking audio player
│   └── engine.py           # Threaded speech worker queue with voice barge-in
├── stt/
│   ├── listener.py         # SpeechRecognition audio capture & transcribe
│   └── wake_word.py        # Wake word detector
├── memory/
│   └── manager.py          # Persistent facts & conversation history manager
├── tools/
│   ├── registry.py         # Universal Tool Registry with dynamic tool lazy-loading
│   ├── web_automator.py    # Playwright & HTTP scraper, price radar, screenshot engine
│   ├── whatsapp_engine.py  # WhatsApp desktop dispatcher
│   ├── email_engine.py     # SMTP/IMAP and native mail automation
│   ├── document_rag.py     # Document indexing, semantic search, and summary engine
│   ├── window_utils.py     # Win32 desktop window targeting and click automation
│   └── contacts_manager.py # Address book manager
└── utils/
    ├── media.py            # Direct YouTube video resolver
    ├── system.py           # Telemetry metrics collection
    └── vision.py           # Multi-modal desktop screen capture
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Windows 10 / 11**
- **Python 3.11+**
- **Microsoft WebView2 Runtime** (pre-installed on modern Windows)

### 2. Installation
Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/IGIRS-AI.git
cd IGIRS-AI
```

Create and activate virtual environment:
```powershell
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:
```powershell
pip install pywebview edge-tts pygame SpeechRecognition psutil pillow
```

### 3. Configure NVIDIA API Key
Create a file named `IGIRS AI (API KEYS).txt` in the root directory (or set the `NVIDIA_API_KEY` environment variable):
```
nvapi-YOUR_NVIDIA_NIM_KEY_HERE
```
*(Get a free key from [build.nvidia.com](https://build.nvidia.com/))*

### 4. Run the Application
```powershell
python run_app.py
```

---

## 📜 License
MIT License. Created by Joshua.
