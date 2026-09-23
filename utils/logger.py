import os
import sys
import logging


class FlushingStreamHandler(logging.StreamHandler):
    """StreamHandler that flushes after every log message for real-time console feedback."""
    def emit(self, record):
        super().emit(record)
        self.flush()


def setup_logger(name="AppLogger", level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # Console handler with immediate flush
        console_handler = FlushingStreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler for persistent logging (app.log)
        try:
            log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.log")
            file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception:
            pass

    return logger

logger = setup_logger("ScreenVoiceAssistant")
