import os
import wave
import math
import struct
from gtts import gTTS

os.makedirs('assets', exist_ok=True)

# Generate "Listening" TTS
gTTS('listening').save('assets/listening.mp3')

# Generate "tu nu nn" sound
def make_tone(freq, duration, sample_rate=44100):
    num_samples = int(duration * sample_rate)
    if freq == 0:
        return [0] * num_samples
    return [int(16000 * math.sin(2 * math.pi * freq * i / sample_rate)) for i in range(num_samples)]

# E5, silence, C5, silence, A4 (descending "tu nu nn")
audio = make_tone(659.25, 0.1) + make_tone(0, 0.05) + make_tone(523.25, 0.1) + make_tone(0, 0.05) + make_tone(440.0, 0.2)

with wave.open('assets/stop.wav', 'w') as f:
    f.setnchannels(1)
    f.setsampwidth(2)
    f.setframerate(44100)
    for sample in audio:
        f.writeframes(struct.pack('<h', sample))
