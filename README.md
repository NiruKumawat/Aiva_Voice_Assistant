# 🎙️ V2 — Screen Voice AI Assistant with Computer Control

A high-performance Windows desktop application that combines **Voice Interaction**, **Real-Time Screen Understanding (Vision AI)**, and **Autonomous Computer Control** (Mouse, Keyboard, Scrolling, and Verification) inside a frosted-glass HUD interface.

Powered by ultra-fast inference via the **Groq API** (`whisper-large-v3-turbo` for Speech-to-Text and `qwen/qwen3.8-27b` for Vision and Action Planning).

---

## 📑 Table of Contents
- [✨ Key Features](#-key-features)
- [💻 System Requirements](#-system-requirements)
- [⚙️ Essential Manual PC Configuration (Before First Run)](#️-essential-manual-pc-configuration-before-first-run)
- [🚀 Quick Setup Guide](#-quick-setup-guide)
- [🎮 Hotkeys & Controls](#-hotkeys--controls)
- [🛠️ Configuration Reference](#️-configuration-reference)
- [🧪 Testing & Verification](#-testing--verification)
- [❓ Troubleshooting & FAQ](#-troubleshooting--faq)

---

## ✨ Key Features

1. **Vision & Screen Understanding**:
   - Actively captures and analyzes application windows, forms, documents, and web pages.
   - Answers contextual questions about what is on your screen using Vision AI.

2. **Computer Control (Autonomous Execution)**:
   - **Mouse Control**: Smooth visual cursor gliding, single-click, double-click, and right-click.
   - **Keyboard Control**: Types text, sends keystrokes, and executes global keyboard shortcuts (`Ctrl+C`, `Enter`, `Alt+Tab`, etc.).
   - **Smooth Scrolling**: Vertical wheel scrolling with speed and duration control.
   - **Multi-Step Execution**: Chains complex actions together (e.g., search Google -> open video -> pause).

3. **Multi-Layer Safety Guardrails**:
   - **Active Window Lock**: Aborts immediately if the active window changes or loses focus.
   - **Boundary Checks**: All mouse coordinates are clamped and validated against primary screen boundaries.
   - **Sensitive Action Gate**: Destructive actions (deletions, payments, form submissions) require spoken or graphical confirmation.
   - **Emergency Stop**: Press `ESC` or click the Stop button at any moment to freeze execution immediately.
   - **Loop Detection**: Stops automatically if consecutive steps leave the screen in an identical state.

4. **Modern Glassmorphic UI**:
   - Floating edge pill with an iridescent pulsating AI orb.
   - Live visual click ripple indicators showing exactly where the AI clicks.
   - Audio sound effects for listening start and stop.

---

## 💻 System Requirements

| Component | Requirement |
| :--- | :--- |
| **Operating System** | **Windows 10 or Windows 11 (64-bit)** *(Windows is strictly required due to Win32 API hooks)* |
| **Python** | **Python 3.10 to 3.12** (Make sure "Add Python to PATH" is checked during installation) |
| **Microphone** | Any working microphone configured as the Windows default recording device |
| **Speakers / Headphones** | Working audio output device for voice responses and sound effects |
| **Network** | Active internet connection (required for Groq AI inference and Google TTS) |

---

## ⚙️ Essential Manual PC Configuration (Before First Run)

Apart from entering your **Groq API Key**, every different PC requires the following manual system settings to function correctly:

### 1. 🛡️ Run Terminal / VS Code as Administrator (CRITICAL)
- **Why**: This app uses the low-level `keyboard` library to register system-wide global hotkeys (`Ctrl+Space`, `Alt+V`, `ESC`). Under Windows User Interface Privilege Isolation (UIPI), non-elevated applications **cannot** intercept keyboard events when an elevated program (e.g., Task Manager, administrative Command Prompt, or certain games) is in focus.
- **Action**: Always right-click **Command Prompt**, **PowerShell**, or **VS Code** and select **"Run as Administrator"** before starting the app.

### 2. 🎤 Enable Windows Microphone Privacy Access
- **Why**: Windows 10/11 includes privacy controls that block desktop applications from reading microphone input by default. If blocked, the app will capture silent audio and STT will return empty text.
- **Action**:
  1. Open Windows **Settings** (`Win + I`).
  2. Go to **Privacy & security** > **Microphone**.
  3. Ensure **"Microphone access"** is turned **ON**.
  4. Ensure **"Let desktop apps access your microphone"** is turned **ON**.

### 3. 🔊 Configure Default Audio Recording & Playback Devices
- **Why**: `sounddevice` automatically connects to the Windows **Default Input Device**. If no microphone is connected or if it is disabled in the Windows Control Panel, the audio recorder will fail on startup.
- **Action**:
  1. Right-click the sound icon in the Windows taskbar and choose **Sound settings**.
  2. Under **Input**, select your active microphone and verify that the input volume bar reacts when you speak.
  3. Under **Output**, ensure your desired speaker or headset is set as Default.

### 4. 🖥️ Display Scaling (DPI) & Multi-Monitor Setup
- **Why**: High-DPI laptops (e.g., 125%, 150%, or 200% Windows display scaling) or multi-monitor setups with mismatched scaling can affect coordinate translation if not handled properly.
- **Note**: The app automatically sets per-monitor DPI awareness (`SetProcessDpiAwareness(2)`). However, for maximum click accuracy:
  - If clicks appear slightly offset, set your primary display scaling to **100%** (Windows Settings > Display > Scale).
  - When using multiple monitors, run the target application on your **primary monitor**.

---

## 🚀 Quick Setup Guide

Follow these steps to set up and run the project on any Windows computer:

### Step 1: Clone the Repository
```bash
git clone https://github.com/<your-username>/<your-repo-name>.git
cd <your-repo-name>
```

### Step 2: Open an Elevated Terminal
Right-click **PowerShell** or **Command Prompt** and select **Run as Administrator**, then navigate to your cloned directory.

### Step 3: Create & Activate Virtual Environment
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment (PowerShell)
.\venv\Scripts\Activate.ps1

# Or activate on Command Prompt (CMD)
# .\venv\Scripts\activate.bat
```

> **Tip for PowerShell execution policy error**: If script execution is restricted, run:
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

### Step 4: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 5: Configure `.env` File
1. Make a copy of `.env.example`:
   ```powershell
   copy .env.example .env
   ```
2. Open `.env` in a text editor and add your Groq API key:
   ```env
   GROQ_API_KEY=gsk_your_groq_api_key_here
   CAPTURE_MODE=FULL_SCREEN
   ```
   *(Get your free Groq API key from [https://console.groq.com/keys](https://console.groq.com/keys))*

### Step 6: (Optional) Verify / Generate Audio Assets
Audio cue files (`assets/listening.mp3` and `assets/stop.wav`) are included. If you ever need to regenerate them:
```bash
python generate_sounds.py
```

### Step 7: Launch the Assistant
```bash
python app.py
```
A floating frosted-glass orb will appear at the right edge of your screen.

---

## 🎮 Hotkeys & Controls

| Action | Shortcut / Trigger | Description |
| :--- | :--- | :--- |
| **Voice Query (Vision + Control)** | `Alt + V` or Mic button on HUD | Captures the active screen and listens for voice instruction |
| **Voice Query (Text Only)** | `Ctrl + Space` | General assistant query without screen context |
| **Emergency Stop** | `ESC` or Red Stop Button on HUD | Instantly aborts any active computer action or speech |
| **Confirm Sensitive Action** | Voice: "Yes" / "Confirm" or UI button | Authorizes a sensitive action (form submit, delete, etc.) |
| **Cancel Sensitive Action** | Voice: "No" / "Cancel" or UI button | Rejects a pending sensitive action |

---

## 🛠️ Configuration Reference

You can customize behavior via `.env` or by editing [`config.py`](file:///d:/Software_project/llm_test/config.py):

| Setting | Default | Description |
| :--- | :--- | :--- |
| `GROQ_API_KEY` | *(None)* | Your Groq API authentication key |
| `CAPTURE_MODE` | `FULL_SCREEN` | `FULL_SCREEN` for entire desktop or `ACTIVE_WINDOW` for foreground window |
| `STT_MODEL` | `whisper-large-v3-turbo` | Groq Speech-to-Text model (~250ms latency) |
| `AI_MODEL` | `qwen/qwen3.8-27b` | Groq Vision & Action planning model |
| `ENABLE_COMPUTER_CONTROL` | `true` | Set `false` to revert to strict read-only assistant mode |
| `ENABLE_FAST_PATH` | `true` | Executes instant direct actions (e.g. scroll, enter) in ~0.2s |
| `ENABLE_ACTION_VERIFICATION` | `false` | Post-action screenshot verification check before next step |
| `REQUIRE_CONFIRMATION_FOR_SENSITIVE_ACTIONS` | `true` | Prompts user before destructive or transactional actions |
| `EMERGENCY_STOP_KEY` | `esc` | Global keyboard key to immediately freeze all execution |
| `MAX_ACTIONS_PER_REQUEST` | `15` | Maximum number of chained steps allowed per request |

---

## 🧪 Testing & Verification

### Run Unit Tests
Run the comprehensive test suite to verify core logic, fast-path dispatch, safety managers, and window watchers:
```bash
python -m unittest discover -p "test_v2_*.py"
```

### Run Live Visual Demo
Watch the AI execute real browser actions on your screen (opens YouTube, moves cursor, searches, plays video):
```bash
python demo_live_execution.py
```

---

## ❓ Troubleshooting & FAQ

#### 1. `ValueError: AI_API_KEY is not set`
- **Fix**: Ensure you have copied `.env.example` to `.env` and populated `GROQ_API_KEY` with a valid key from [Groq Console](https://console.groq.com/keys). Make sure `.env` is in the root directory.

#### 2. Hotkeys (`Ctrl+Space` or `Alt+V`) do not respond
- **Fix**: You must run your terminal or editor **As Administrator**. Windows prevents non-admin apps from capturing global keyboard hooks when any administrative window has focus.

#### 3. `sounddevice.PortAudioError: Error querying device` or microphone records silence
- **Fix**: 
  - Ensure Windows Microphone Privacy is enabled (**Settings > Privacy & security > Microphone**).
  - Verify that a physical microphone is plugged in and set as the default device in the Windows Sound control panel.

#### 4. Mouse clicks are slightly off target
- **Fix**: Check Windows Display Scaling (**Settings > System > Display > Scale**). While Per-Monitor DPI scaling is handled automatically, setting the display scale to 100% on the primary monitor guarantees pixel-perfect accuracy across all legacy Win32 apps.

#### 5. PyWin32 DLL Load Error
- **Fix**: If you encounter `ImportError: DLL load failed while importing win32api`, run:
  ```bash
  python venv/Scripts/pywin32_postinstall.py -install
  ```

---

## 🔒 Security Best Practices
- **Never commit `.env` to Git**: `.env` contains your personal API keys and is excluded via `.gitignore`.
- **Revoke exposed keys**: If you accidentally commit or expose an API key, immediately revoke it on [console.groq.com](https://console.groq.com/keys) and generate a new one.
#   V o i c e _ A s s i s t a n c e  
 