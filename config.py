import os
from dotenv import load_dotenv

load_dotenv()

APP_NAME = "Screen Voice Assistant"

# API Keys
AI_API_KEY = os.getenv("GROQ_API_KEY")

# Model Configuration
STT_MODEL = os.getenv("STT_MODEL", "whisper-large-v3-turbo")  # 4x faster transcription (~250ms)
# Qwen 3.8 27B from Groq (Vision supported)
AI_MODEL = os.getenv("AI_MODEL", "qwen/qwen3.8-27b")
AI_TEXT_MODEL = os.getenv("AI_TEXT_MODEL", "qwen/qwen3.8-27b")

# Capture Settings
CAPTURE_MODE = os.getenv("CAPTURE_MODE", "FULL_SCREEN")  # "FULL_SCREEN" or "ACTIVE_WINDOW"
MAX_IMAGE_SIZE = (1920, 1080)  # Preserves native resolution up to 1080p without downscaling distortion

# Continuous Screen Watcher Settings
ENABLE_CONTINUOUS_SCREEN_WATCHER = os.getenv("ENABLE_CONTINUOUS_SCREEN_WATCHER", "true").lower() == "true"
SCREEN_WATCHER_INTERVAL = float(os.getenv("SCREEN_WATCHER_INTERVAL", "1.5"))  # Seconds between change checks (<0.2% CPU)
AUTO_VISION_VOICE = os.getenv("AUTO_VISION_VOICE", "true").lower() == "true"  # Automatically use live screen buffer on voice

# Hotkeys
HOTKEY = "ctrl+space"  # Voice command (uses live screen automatically when AUTO_VISION_VOICE is true)
HOTKEY_VISION = "ctrl+shift+space"  # Explicit manual screenshot capture

# --- V2 Computer Control & Speed Settings ---
ENABLE_COMPUTER_CONTROL = os.getenv("ENABLE_COMPUTER_CONTROL", "true").lower() == "true"
ENABLE_FAST_PATH = os.getenv("ENABLE_FAST_PATH", "true").lower() == "true"  # Instant 0.2s dispatch for scroll/enter/keys
ENABLE_ACTION_VERIFICATION = os.getenv("ENABLE_ACTION_VERIFICATION", "false").lower() == "true"  # Set false to skip 20s delay
MAX_ACTIONS_PER_REQUEST = int(os.getenv("MAX_ACTIONS_PER_REQUEST", "15"))
REQUIRE_CONFIRMATION_FOR_SENSITIVE_ACTIONS = os.getenv("REQUIRE_CONFIRMATION_FOR_SENSITIVE_ACTIONS", "true").lower() == "true"
EMERGENCY_STOP_KEY = os.getenv("EMERGENCY_STOP_KEY", "esc")
SHOW_ACTION_INDICATOR = os.getenv("SHOW_ACTION_INDICATOR", "true").lower() == "true"
MAX_IDENTICAL_SCREEN_STATES = 3

# Capabilities Configuration
CAPABILITIES = {
    "screen_capture": True,
    "microphone": True,
    "speech_to_text": True,
    "vision": True,
    "text_to_speech": True,

    "mouse_control": ENABLE_COMPUTER_CONTROL,
    "keyboard_control": ENABLE_COMPUTER_CONTROL,
    "scroll_control": ENABLE_COMPUTER_CONTROL,
    "application_control": False,
    "file_modification": False,
}
