from groq import Groq
from config import AI_API_KEY, AI_MODEL, AI_TEXT_MODEL
from utils.logger import logger

system_prompt = """You are a screen-understanding voice assistant. 
The image provided is a screenshot of the user's currently visible screen or active window. 
Answer the user's question using the visible information in the screenshot.
Keep your answers SHORT and CONCISE — ideally 2-4 sentences. You will be read aloud via text-to-speech, so avoid markdown, bullet points, or long lists.
Do not claim to see information that is not visible. 
If the requested information is not visible, clearly say so.
For questions about locations of UI elements, describe their approximate location briefly.
You are read-only: you cannot interact with the computer."""

text_system_prompt = """You are a helpful voice assistant.
Keep your answers SHORT and CONCISE — ideally 2-4 sentences. You will be read aloud via text-to-speech, so avoid markdown, bullet points, or long lists."""

def ask_vision_ai(question: str, base64_image: str = None, history: list = None) -> str:
    """
    Sends the user's question (and optionally screen capture) to the AI model, along with conversation history.
    """
    if not AI_API_KEY:
        raise ValueError("AI_API_KEY is not set.")
        
    client = Groq(api_key=AI_API_KEY)
    
    use_vision = bool(base64_image)
    model_to_use = AI_MODEL if use_vision else AI_TEXT_MODEL
    logger.info(f"Sending request to {model_to_use} (vision: {use_vision})...")
    
    messages = [
        {
            "role": "system",
            "content": system_prompt if use_vision else text_system_prompt
        }
    ]
    
    if history:
        messages.extend(history)
    
    if use_vision:
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": question},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]
        })
    else:
        messages.append({
            "role": "user",
            "content": question
        })
    
    try:
        completion = client.chat.completions.create(
            model=model_to_use,
            messages=messages,
            temperature=0.7 if not use_vision else 0.1,
            max_tokens=512
        )
        
        answer = completion.choices[0].message.content
        logger.info(f"AI response received: {answer}")
        return answer
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "I encountered an error while trying to process your request. Please try again."
