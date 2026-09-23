import os
from groq import Groq
from config import AI_API_KEY, STT_MODEL
from utils.logger import logger

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
                response_format="text"
            )
        
        # Depending on the SDK version, the response might be a string or object.
        # response_format="text" typically returns a string directly.
        text = str(transcription).strip()
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
