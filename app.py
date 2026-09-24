import sys
import os
import time
import ctypes
import threading
import keyboard
import win32gui
from PySide6.QtWidgets import QApplication
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl, Signal, QObject

from config import HOTKEY, HOTKEY_VISION, ENABLE_COMPUTER_CONTROL, EMERGENCY_STOP_KEY, AUTO_VISION_VOICE, ENABLE_CONTINUOUS_SCREEN_WATCHER, HIDE_ORB_FROM_SCREEN_CAPTURE
from utils.logger import logger
from capture.screen import capture_screen
from capture.watcher import ScreenWatcher
from audio.recorder import AudioRecorder
from audio.speech_to_text import transcribe_audio
from ai.vision_assistant import ask_vision_ai
from audio.text_to_speech import TTSPlayer
from ui.main_window import MainWindow
from ui.action_indicator import init_action_indicator
from agent.loop import AgentLoop

# Set DPI awareness BEFORE QApplication is created so all coordinate APIs
# (GetSystemMetrics, mss, pyautogui) operate in the same physical pixel space.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    logger.info("DPI awareness set to Per-Monitor DPI Aware (level 2)")
except Exception as e:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
        logger.info("DPI awareness set via SetProcessDPIAware fallback")
    except Exception:
        logger.warning(f"Could not set DPI awareness: {e}")


class VoiceAssistantApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.window = MainWindow()
        self.action_indicator = init_action_indicator()
        self.tts_player = TTSPlayer()
        self.recorder = AudioRecorder()

        # Optionally exclude assistant window from screen capture APIs
        # Default is False so screen recording tools (like Loom / OBS) capture the HUD during demos.
        self._window_hwnd = int(self.window.winId())
        if HIDE_ORB_FROM_SCREEN_CAPTURE:
            try:
                WDA_EXCLUDEFROMCAPTURE = 0x00000011
                result = ctypes.windll.user32.SetWindowDisplayAffinity(self._window_hwnd, WDA_EXCLUDEFROMCAPTURE)
                if result:
                    logger.info(f"Window HWND {self._window_hwnd} excluded from screen capture via SetWindowDisplayAffinity")
                else:
                    logger.warning("SetWindowDisplayAffinity failed")
            except Exception as e:
                logger.warning(f"Could not set display affinity: {e}")
        else:
            logger.info("Orb display capture affinity is enabled (visible in Loom / screen recording)")

        # V2 Computer Control Agent Loop
        self.agent_loop = AgentLoop(
            status_callback=lambda s: self.window.update_status_signal.emit(s),
            tts_callback=self._on_tts_ready
        )
        
        # Always-Ready Screen Watcher (< 0.2% CPU, zero API calls when idle)
        self.screen_watcher = ScreenWatcher(
            on_change_callback=self._on_screen_changed
        )
        if ENABLE_CONTINUOUS_SCREEN_WATCHER:
            self.screen_watcher.start()
        
        # Player for UI sound effects
        self.ui_player = QMediaPlayer()
        self.ui_audio_output = QAudioOutput()
        self.ui_player.setAudioOutput(self.ui_audio_output)
        self.ui_player.setPlaybackRate(1.5)
        
        # Resolve asset paths
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.listening_sound = os.path.join(base_dir, 'assets', 'listening.mp3')
        self.stop_sound = os.path.join(base_dir, 'assets', 'stop.wav')
        
        self.is_processing = False
        self.is_recording = False
        self.current_image = None
        self.current_window_title = ""
        self.last_hotkey_time = 0  # Debounce hotkey
        self.chat_history = []  # Keep track of conversation context
        
        # Connect UI signals
        self.window.start_listening_signal.connect(lambda: self.toggle_recording(use_vision=True))
        self.window.play_audio_signal.connect(self._on_tts_ready)
        self.window.tts_play_signal.connect(self.tts_player.play_generated)
        self.window.play_ui_sound_signal.connect(self._play_ui_sound_internal)
        self.window.hotkey_signal.connect(lambda: self.toggle_recording(use_vision=False))
        self.window.hotkey_vision_signal.connect(lambda: self.toggle_recording(use_vision=True))
        self.window.open_settings_signal.connect(self.open_settings)

        # Connect V2 Computer Control Signals
        self.window.confirm_action_signal.connect(self.on_ui_confirm)
        self.window.cancel_action_signal.connect(self.on_ui_cancel)
        self.window.emergency_stop_signal.connect(self.on_emergency_stop)
        
        # Connect TTS playback finished to reset state
        self.tts_player.playback_finished_signal.connect(self.reset_state)
        
        # Register global hotkeys
        try:
            keyboard.add_hotkey(HOTKEY, self.on_hotkey)
            keyboard.add_hotkey(HOTKEY_VISION, self.on_hotkey_vision)
            keyboard.add_hotkey(EMERGENCY_STOP_KEY, self.on_emergency_stop)
            logger.info(f"Registered global hotkeys: {HOTKEY} (Text), {HOTKEY_VISION} (Vision), {EMERGENCY_STOP_KEY} (Stop)")
        except Exception as e:
            logger.error(f"Failed to register hotkeys: {e}")



    def on_hotkey(self):
        """Called by the keyboard listener thread (Text mode)."""
        if self._debounce(): return
        self.window.hotkey_signal.emit()

    def on_hotkey_vision(self):
        """Called by the keyboard listener thread (Vision mode)."""
        if self._debounce(): return
        self.window.hotkey_vision_signal.emit()

    def on_emergency_stop(self):
        """Immediately aborts active action execution or TTS."""
        logger.warning("Emergency stop triggered!")
        self.agent_loop.stop()
        self.tts_player.stop()
        self.window.hide_confirmation_signal.emit()
        self.window.update_status_signal.emit("Stopped")
        self.window.update_answer_signal.emit("Action stopped by user.")
        self.reset_state()

    def on_ui_confirm(self):
        """Called when user clicks 'Confirm (Yes)' button in UI."""
        if not self.agent_loop.pending_confirmation:
            return
        self.window.hide_confirmation_signal.emit()
        self.window.update_status_signal.emit("Executing confirmed action...")
        self.is_processing = True
        threading.Thread(target=self._run_confirmed_action, daemon=True).start()

    def _run_confirmed_action(self):
        try:
            answer = self.agent_loop.execute_confirmed_plan()
            self.chat_history.append({"role": "assistant", "content": answer})
            self.window.update_answer_signal.emit(answer)
            self.window.update_status_signal.emit("Speaking...")
            self.window.play_audio_signal.emit(answer)
        except Exception as e:
            logger.error(f"Error executing confirmed action: {e}")
            self.window.update_answer_signal.emit("An error occurred during execution.")
            self.reset_state()

    def on_ui_cancel(self):
        """Called when user clicks 'Cancel (No)' button in UI."""
        self.window.hide_confirmation_signal.emit()
        msg = self.agent_loop.cancel_pending_confirmation()
        self.window.update_answer_signal.emit(msg)
        self.window.play_audio_signal.emit(msg)
        self.reset_state()

    def _debounce(self):
        now = time.time()
        if now - self.last_hotkey_time < 1.0:
            return True
        self.last_hotkey_time = now
        return False

    def toggle_recording(self, use_vision=False):
        """Toggles between recording and processing state."""
        if self.is_processing:
            return
            
        if not self.is_recording:
            self.start_recording(use_vision)
        else:
            self.stop_recording_and_process(use_vision)

    def open_settings(self):
        """Open the config.py file in the default text editor."""
        try:
            os.startfile('config.py')
        except Exception as e:
            logger.error(f"Failed to open settings: {e}")

    def play_ui_sound(self, file_path):
        """Emit signal to play UI sound safely on main thread."""
        self.window.play_ui_sound_signal.emit(file_path)

    def _play_ui_sound_internal(self, file_path):
        """Actual playback (must run on main thread)."""
        if os.path.exists(file_path):
            self.ui_player.setSource(QUrl.fromLocalFile(file_path))
            self.ui_player.play()

    def _on_tts_ready(self, text):
        """Generate TTS in a thread, then play on main thread."""
        threading.Thread(target=self._generate_and_play_tts, args=(text,), daemon=True).start()

    def _generate_and_play_tts(self, text):
        """Background thread: generate the TTS file, then emit signal to play on main thread."""
        self.tts_player.generate(text)
        self.window.update_status_signal.emit("Speaking...")
        # Emit signal so playback happens on the main Qt thread
        self.window.tts_play_signal.emit()

    def _on_screen_changed(self, screen_data):
        """Called by ScreenWatcher when active window or screen changes."""
        if not self.is_recording and not self.is_processing:
            self.window.update_window_signal.emit(screen_data.window_title)

    def start_recording(self, use_vision=False):
        self.is_recording = True
        self.play_ui_sound(self.listening_sound)
        effective_vision = use_vision or AUTO_VISION_VOICE
        mode = "Vision" if effective_vision else "Chat"
        self.window.update_status_signal.emit(f"\U0001f3a4 Listening ({mode})...")
        self.window.update_question_signal.emit("")
        self.window.update_answer_signal.emit("")
        
        if effective_vision:
            try:
                # Instantly retrieve latest screen from always-ready ScreenWatcher buffer (0ms delay)
                screen_data = self.screen_watcher.get_latest_screen()
                self.current_image = screen_data.image_b64
                self.current_window_title = screen_data.window_title
                self.window.update_window_signal.emit(self.current_window_title)
            except Exception as e:
                logger.error(f"Failed to get screen from watcher: {e}")
                self.current_image, self.current_window_title = capture_screen()
                self.window.update_window_signal.emit(self.current_window_title)
        else:
            self.current_image = None
            self.window.update_window_signal.emit("N/A (Text Mode)")
            
        self.recorder.start_recording()

    def stop_recording_and_process(self, use_vision=False):
        self.is_recording = False
        self.is_processing = True
        self.play_ui_sound(self.stop_sound)
        self.window.update_status_signal.emit("Processing...")
        
        audio_file = self.recorder.stop_recording()
        
        if not audio_file:
            self.reset_state()
            return
            
        # Process in a background thread to keep UI responsive
        effective_vision = use_vision or AUTO_VISION_VOICE
        threading.Thread(target=self.process_pipeline, args=(audio_file, effective_vision), daemon=True).start()

    def process_pipeline(self, audio_file, use_vision=False):
        try:
            # 1. Speech to text
            self.window.update_status_signal.emit("Transcribing...")
            question = transcribe_audio(audio_file)
            
            if not question:
                self.window.update_status_signal.emit("Could not hear anything.")
                self.reset_state()
                return
                
            self.window.update_question_signal.emit(question)

            # Check if answering a pending confirmation
            if self.agent_loop.pending_confirmation:
                is_affirmative = self.agent_loop.safety.confirmation.parse_confirmation_response(question)
                if is_affirmative is True:
                    self.window.hide_confirmation_signal.emit()
                    self.window.update_status_signal.emit("Confirmed. Executing...")
                    answer = self.agent_loop.execute_confirmed_plan()
                    self.chat_history.append({"role": "user", "content": question})
                    self.chat_history.append({"role": "assistant", "content": answer})
                    self.window.update_answer_signal.emit(answer)
                    self.window.play_audio_signal.emit(answer)
                    return
                elif is_affirmative is False:
                    self.window.hide_confirmation_signal.emit()
                    answer = self.agent_loop.cancel_pending_confirmation()
                    self.chat_history.append({"role": "user", "content": question})
                    self.chat_history.append({"role": "assistant", "content": answer})
                    self.window.update_answer_signal.emit(answer)
                    self.window.play_audio_signal.emit(answer)
                    return
                else:
                    # Unrelated response: cancel pending action and treat as new command
                    self.agent_loop.cancel_pending_confirmation()
                    self.window.hide_confirmation_signal.emit()
            
            if use_vision and not self.current_image:
                self.window.update_answer_signal.emit("No screenshot available to analyze.")
                self.reset_state()
                return

            # 2. AI reasoning / Agent execution
            if ENABLE_COMPUTER_CONTROL or use_vision:
                self.window.update_status_signal.emit("Thinking...")
                answer = self.agent_loop.run_cycle(question, self.chat_history)

                # Check if emergency stop occurred during run_cycle
                if self.agent_loop.safety.emergency_stop.is_stop_requested():
                    logger.info("Process pipeline -> Stop requested; skipping TTS.")
                    self.reset_state()
                    return

                # Check if confirmation is required before proceeding
                if self.agent_loop.pending_confirmation:
                    prompt = answer
                    self.window.show_confirmation_signal.emit(prompt)
                    self.window.update_status_signal.emit("Confirmation Required")
                    self.window.update_answer_signal.emit(prompt)
                    self.window.play_audio_signal.emit(prompt)
                    self.is_processing = False
                    return
            else:
                self.window.update_status_signal.emit("Thinking...")
                answer = ask_vision_ai(question, None, self.chat_history)
            
            # Update history (store text only to avoid bloat)
            self.chat_history.append({"role": "user", "content": question})
            self.chat_history.append({"role": "assistant", "content": answer})
            
            # Keep only the last 10 messages (5 conversational turns)
            if len(self.chat_history) > 10:
                self.chat_history = self.chat_history[-10:]
                
            self.window.update_answer_signal.emit(answer)
            
            # 3. Text to speech (generate in background, play on main thread)
            self.window.update_status_signal.emit("Generating voice...")
            self.window.play_audio_signal.emit(answer)
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            self.window.update_answer_signal.emit("An error occurred during processing.")
            self.reset_state()

    def reset_state(self):
        self.is_processing = False
        self.window.update_status_signal.emit("Ready")

    def run(self):
        self.window.show()
        ret = self.app.exec()
        if hasattr(self, 'screen_watcher') and self.screen_watcher:
            self.screen_watcher.stop()
        return ret

if __name__ == "__main__":
    app = VoiceAssistantApp()
    sys.exit(app.run())
