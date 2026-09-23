import sounddevice as sd
import soundfile as sf
import tempfile
import os
from utils.logger import logger

class AudioRecorder:
    def __init__(self, samplerate=16000, channels=1):
        self.samplerate = samplerate
        self.channels = channels
        self.recording = False
        self.frames = []
        self.stream = None

    def _callback(self, indata, frames, time, status):
        if status:
            logger.warning(f"Audio status: {status}")
        if self.recording:
            self.frames.append(indata.copy())

    def start_recording(self):
        self.frames = []
        self.recording = True
        self.stream = sd.InputStream(samplerate=self.samplerate,
                                     channels=self.channels,
                                     callback=self._callback)
        self.stream.start()
        logger.info("Recording started...")

    def stop_recording(self) -> str:
        self.recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            
        logger.info("Recording stopped.")
        
        if not self.frames:
            logger.warning("No audio frames recorded.")
            return None
            
        import numpy as np
        audio_data = np.concatenate(self.frames, axis=0)
        
        # Save to temporary file
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, "temp_voice_assistant_record.wav")
        
        sf.write(file_path, audio_data, self.samplerate)
        logger.info(f"Audio saved to {file_path}")
        return file_path
