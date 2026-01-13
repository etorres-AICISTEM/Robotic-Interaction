import speech_recognition as sr
import os
import sys
from ctypes import *
import whisper
import vosk
import json
import pyaudio
from openai import OpenAI
from gtts import gTTS

# Initialize NVIDIA Nemotron API client
NVIDIA_API_KEY = "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"

try:
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=NVIDIA_API_KEY
    )
    print("✓ NVIDIA Nemotron initialized")
except Exception as e:
    print(f"Warning: Could not initialize Nemotron: {e}")
    client = None

# Suppress ALSA warnings
ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
def py_error_handler(filename, line, function, err, fmt):
    pass
c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
try:
    asound = cdll.LoadLibrary('libasound.so.2')
    asound.snd_lib_error_set_handler(c_error_handler)
except (OSError, AttributeError):
    pass

# Vosk model setup
MODEL_PATH = "model"  # Download from https://alphacephei.com/vosk/models
if not os.path.exists(MODEL_PATH):
    print("Error: Model not found. Download a model from https://alphacephei.com/vosk/models")
    print("Extract it and rename to 'model' in the current directory")
    sys.exit(1)

vosk.SetLogLevel(-1)  # Suppress debug logs
model = vosk.Model(MODEL_PATH)
recognizer = vosk.KaldiRecognizer(model, 16000)
recognizer.SetWords(["jarvis"])  # Wake word to detect

# PyAudio setup with error handling
p = pyaudio.PyAudio()

# Try to open stream with different configurations
stream = None
configurations = [
    {"channels": 2, "rate": 48000},
    {"channels": 1, "rate": 48000},
    {"channels": 2, "rate": 44100},
    {"channels": 1, "rate": 44100},
    {"channels": 2, "rate": 16000},
    {"channels": 1, "rate": 16000},
]

for config in configurations:
    try:
        stream = p.open(
            format=pyaudio.paInt16,
            channels=config["channels"],
            rate=config["rate"],
            input=True,
            input_device_index=16,
            frames_per_buffer=2048
        )
        print(f"✓ Stream opened with {config['channels']} channels at {config['rate']} Hz")
        vosk_rate = config["rate"]
        vosk_channels = config["channels"]
        break
    except OSError as e:
        print(f"✗ Failed with {config['channels']} channels at {config['rate']} Hz")
        continue

if stream is None:
    print("Error: Could not open audio stream with device 24. Falling back to default device.")
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=2048)
    vosk_rate = 16000
    vosk_channels = 1

stream.start_stream()

print("🎤 Listening for wake word 'jarvis'...")

# Wake word detection loop
wake_word_detected = False
while not wake_word_detected:
    try:
        data = stream.read(2048, exception_on_overflow=False)
        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            if "result" in result and result["result"]:
                text = " ".join([item.get("result", "") for item in result["result"]]).lower()
                if "jarvis" in text:
                    print("✓ Wake word detected!")
                    wake_word_detected = True
                    break
        else:
            # Check partial results for wake word
            partial = json.loads(recognizer.PartialResult())
            if "partial" in partial:
                partial_text = partial["partial"].lower()
                if "jarvis" in partial_text:
                    print(f"✓ Wake word detected: {partial_text}")
                    wake_word_detected = True
                    break
    except (OSError, json.JSONDecodeError) as e:
        continue

# Conversation loop
conversation_history = []
exit_keywords = ["gracias", "chao", "hasta luego", "adiós", "bye", "exit", "quit"]
conversation_active = True

print("\n💬 Starting conversation... Say 'gracias' to exit")

while conversation_active:
    # Listen for command/question
    print("\n🎤 Listening for your command...")
    command_text = ""
    listening_for_command = True
    timeout_frames = 0
    last_partial = ""

    while listening_for_command:
        try:
            data = stream.read(2048, exception_on_overflow=False)
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                if "result" in result and result["result"]:
                    command_text = " ".join([item.get("result", "") for item in result["result"]]).lower()
                    if command_text.strip():
                        print(f"✓ Command captured: {command_text}")
                        listening_for_command = False
                        break
            else:
                # Capture partial results
                partial = json.loads(recognizer.PartialResult())
                if "partial" in partial and partial["partial"].strip():
                    last_partial = partial["partial"].lower()
                    print(f"Listening: {last_partial}", end='\r')
                    timeout_frames = 0  # Reset timeout when we hear something
                timeout_frames += 1
                # If we get 2 seconds of silence after hearing something, break
                if timeout_frames > int(16000 * 2 / 2048) and last_partial:
                    command_text = last_partial
                    print(f"\n✓ Command captured: {command_text}")
                    listening_for_command = False
                    break
        except (OSError, json.JSONDecodeError) as e:
            continue

    spoken_text = command_text if command_text else "No command detected"
    print(f"📝 You said: {spoken_text}")

    # Check for exit keywords
    if any(keyword in spoken_text for keyword in exit_keywords):
        print("\n👋 Conversation ended. Goodbye!")
        conversation_active = False
        break

    # Send to Nemotron for intelligent response
    answer = None
    if client and spoken_text.strip() and spoken_text != "No command detected":
        try:
            print("⏳ Getting response from Nemotron...")
            
            # Add user message to history
            conversation_history.append({"role": "user", "content": spoken_text})
            
            # Create messages with context
            messages = conversation_history.copy()
            
            response = client.chat.completions.create(
                model="nvidia/nvidia-nemotron-nano-9b-v2",
                messages=messages,
                temperature=0.7,
                max_tokens=512
            )
            answer = response.choices[0].message.content.strip()
            print(f"🤖 Nemotron: {answer}")
            
            # Add assistant response to history
            conversation_history.append({"role": "assistant", "content": answer})
            
        except Exception as e:
            print(f"Error getting response from Nemotron: {e}")
            print("Trying alternative model...")
            try:
                response = client.chat.completions.create(
                    model="meta/llama2-70b",
                    messages=conversation_history if conversation_history else [{"role": "user", "content": spoken_text}],
                    temperature=0.7,
                    max_tokens=512
                )
                answer = response.choices[0].message.content.strip()
                print(f"🤖 Response: {answer}")
                conversation_history.append({"role": "assistant", "content": answer})
            except Exception as e2:
                print(f"Error with fallback model: {e2}")
    else:
        print("No command to process")

    # Text-to-Speech for the response
    if answer:
        try:
            print("🔊 Generating speech...")
            tts = gTTS(answer, lang='es')
            tts.save("response.mp3")
            print("🔊 Playing response...")
            os.system("mpg123 -q response.mp3 2>/dev/null")
            print("✓ Speech played")
        except Exception as e:
            print(f"Error in text-to-speech: {e}")

# Cleanup
stream.stop_stream()
stream.close()
p.terminate()
print("✓ Audio stream closed")
 