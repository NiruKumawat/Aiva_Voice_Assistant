import os
from groq import Groq
from config import AI_API_KEY, STT_MODEL
from utils.logger import logger

# Context prompt biasing Whisper towards Windows applications and standard desktop voice actions
WHISPER_PROMPT = (
    "AIVA desktop voice assistant commands for Windows. "
    "Applications and actions: Notepad, Chrome, YouTube, File Explorer, Calculator, VS Code, "
    "new file, open file, save file, clear all, select all, copy text, paste, search, close tab, close window."
)

PHONETIC_CORRECTIONS = {
    r"\bnot\s*paid\b": "Notepad",
    r"\bnot\s*prid\b": "Notepad",
    r"\bnote\s*pad\b": "Notepad",
    r"\bopenrid\s*notprid\b": "Open Notepad",
    r"\bnew\s*pile\b": "new file",
    r"\btake\s*a\s*new\s*pile\b": "take a new file",
    r"\bchrome\s*brower\b": "Chrome browser",
}


def transcribe_audio(audio_file_path: str) -> str:
    """
    Transcribes the audio file using Groq Whisper API.
    Returns the transcribed text.
    """
    if not AI_API_KEY:
        raise ValueError("AI_API_KEY is not set.")
        
    client = Groq(api_key=AI_API_KEY)
    
    logger.info(f"Transcribing {audio_file_path} using {STT_MODEL}...")
    
    try:
        with open(audio_file_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(audio_file_path), file.read()),
                model=STT_MODEL,
                prompt=WHISPER_PROMPT,
                response_format="text"
            )
        
        # Clean text
        text = str(transcription).strip()

        # Apply phonetic corrections for common desktop voice misrecognitions
        import re
        for pattern, replacement in PHONETIC_CORRECTIONS.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        logger.info(f"Transcription complete: {text}")
        return text
    except Exception as e:
        logger.error(f"STT Error: {e}")
        return ""
    finally:
        # Clean up temporary file
        try:
            if os.path.exists(audio_file_path):
                os.remove(audio_file_path)
        except Exception as cleanup_error:
            logger.warning(f"Failed to delete temp audio file: {cleanup_error}")
