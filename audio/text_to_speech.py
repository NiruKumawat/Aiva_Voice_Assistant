import os
import tempfile
import uuid
from gtts import gTTS
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl, QObject, QMetaObject, Qt, Q_ARG, Signal
from utils.logger import logger

class TTSPlayer(QObject):
    playback_finished_signal = Signal()
    def __init__(self):
        super().__init__()
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setPlaybackRate(1.1)  # Slightly faster than normal
        self.audio_output.setVolume(1.0)
        self.current_temp_file = None
        self.pending_file = None  # File generated in background, waiting to play
        
        # Clean up file when playback stops
        self.player.playbackStateChanged.connect(self._on_state_changed)

    def _on_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.StoppedState:
            # Use QTimer to schedule cleanup to avoid deadlocking the Qt event loop
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, self._do_cleanup_and_signal)

    def _do_cleanup_and_signal(self):
        self._cleanup_temp_file()
        self.playback_finished_signal.emit()

    def _cleanup_temp_file(self):
        if self.current_temp_file and os.path.exists(self.current_temp_file):
            try:
                self.player.setSource(QUrl()) # Release file lock
                os.remove(self.current_temp_file)
                self.current_temp_file = None
            except Exception as e:
                logger.warning(f"Failed to delete temp TTS file: {e}")

    def generate(self, text: str):
        """Generate TTS audio file (safe to call from any thread)."""
        if not text:
            return
            
        logger.info("Generating TTS...")
        try:
            tts = gTTS(text=text, lang='en')
            temp_dir = tempfile.gettempdir()
            # Use unique filename to avoid file conflicts
            file_path = os.path.join(temp_dir, f"tts_{uuid.uuid4().hex[:8]}.mp3")
            tts.save(file_path)
            self.pending_file = file_path
            logger.info(f"TTS file generated: {file_path}")
        except Exception as e:
            logger.error(f"TTS Generation Error: {e}")
            self.pending_file = None

    def play_generated(self):
        """Play the previously generated TTS file (must be called from main thread)."""
        if not self.pending_file or not os.path.exists(self.pending_file):
            logger.warning("No TTS file to play.")
            self.playback_finished_signal.emit()
            return
            
        try:
            # Clean up old file if any
            self._cleanup_temp_file()
            self.current_temp_file = self.pending_file
            self.pending_file = None
            
            # Play
            self.player.setSource(QUrl.fromLocalFile(self.current_temp_file))
            self.player.play()
            logger.info("Playing audio...")
            
        except Exception as e:
            logger.error(f"TTS Playback Error: {e}")

    def stop(self):
        """Stops playback and cleans up immediately."""
        try:
            self.player.stop()
            self._cleanup_temp_file()
        except Exception as e:
            logger.warning(f"Failed to stop TTS player: {e}")

    def speak(self, text: str):
        """Generate and play TTS (convenience method, blocks during generation)."""
        self.generate(text)
        self.play_generated()

