import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
TEMP_AUDIO_DIR = BASE_DIR / "temp_audio"
TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

FACTS_FILE = BASE_DIR / "facts_store.json"
MEMORY_FILE = BASE_DIR / "memory_store.json"
NOTES_FILE = BASE_DIR / "notes_store.json"
API_KEYS_FILE = BASE_DIR / "IGIRS AI (API KEYS).txt"

# Load NVIDIA API Keys (Multi-key support with auto-rotation)
NVIDIA_API_KEYS = []

if API_KEYS_FILE.exists():
    with open(API_KEYS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            clean_key = line.strip()
            if clean_key and not clean_key.startswith("#"):
                NVIDIA_API_KEYS.append(clean_key)

# Check environment variable as additional fallback
env_key = os.environ.get("NVIDIA_API_KEY")
if env_key and env_key not in NVIDIA_API_KEYS:
    NVIDIA_API_KEYS.append(env_key)

# Default fallback keys from workspace
if not NVIDIA_API_KEYS:
    NVIDIA_API_KEYS = [
        "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",
        "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",
        "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"
    ]

# LLM Configuration (NVIDIA NIM Active Models)
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
PRIMARY_LLM_MODEL = "meta/llama-3.2-11b-vision-instruct"
FALLBACK_LLM_MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b",
    "deepseek-ai/deepseek-v4-pro-0813"
]

LLM_TEMPERATURE = 0.6
LLM_MAX_TOKENS = 150

# TTS Configuration (Edge-TTS & Neural Voices)
VOICE_ENABLED_DEFAULT = True
DEFAULT_ENGLISH_VOICE = "en-US-ChristopherNeural"
DEFAULT_TAMIL_VOICE = "ta-IN-PallaviNeural"
FALLBACK_ENGLISH_VOICE = "en-US-AndrewNeural"
DEFAULT_TTS_RATE = "+14%"
DEFAULT_TTS_VOLUME = 1.0  # Range: 0.0 to 1.0

# User Identity & Defaults
DEFAULT_USER_NAME = "Joshua"
ASSISTANT_NAME = "IGIRS AI"
LANGUAGE_PREFERENCE = "English"
