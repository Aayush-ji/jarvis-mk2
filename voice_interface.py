# =============================================================================
# J.A.R.V.I.S. Mk.II — Voice Interface (Local)
# =============================================================================
# Wake-word listener ("Hey Jarvis"), speech-to-text, text-to-speech, and
# intent routing that dispatches commands to the JarvisClient.
# =============================================================================

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    print("[JARVIS Voice] speech_recognition not available — voice input disabled. "
          "Intent router can still be tested by calling handle_voice() directly.")

# Check for PyAudio separately (needed for microphone access)
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    print("[JARVIS Voice] pyaudio not available — microphone input disabled. "
          "Intent router can still be tested by calling handle_voice() directly.")

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False
    print("[JARVIS Voice] pyttsx3 not available — text-to-speech disabled.")


class JarvisVoice:
    def __init__(self, client):
        self.client = client
        self.recognizer = sr.Recognizer() if SPEECH_RECOGNITION_AVAILABLE else None
        self.microphone = sr.Microphone() if (SPEECH_RECOGNITION_AVAILABLE and PYAUDIO_AVAILABLE) else None
        self.engine = pyttsx3.init() if PYTTSX3_AVAILABLE else None
        if self.engine:
            self.engine.setProperty("rate", 175)
        self.wake_word = "hey jarvis"
        self.listening_for_wake = True

        # Calibrate microphone once on startup (if available)
        if self.microphone is not None:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)

    def speak(self, text: str):
        """Text-to-speech output."""
        if not PYTTSX3_AVAILABLE or not self.engine:
            print(f"[JARVIS TTS] {text}")
            return
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"[JARVIS Voice] TTS error: {e}")

    def listen(self) -> str:
        """Blocking listen. Returns transcribed text or empty string."""
        if self.microphone is None:
            return ""
        try:
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=6)
            text = self.recognizer.recognize_google(audio)
            return text
        except sr.WaitTimeoutError:
            return ""
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            print(f"[JARVIS Voice] STT service error: {e}")
            return ""
        except Exception as e:
            print(f"[JARVIS Voice] Listen error: {e}")
            return ""

    def type_command(self, text: str):
        """Type a command instead of speaking it. Useful for demos without PyAudio."""
        print(f"\n[JARVIS] Typed input: {text}")
        return text

    async def handle_voice(self, text: str):
        """Route recognised speech to the appropriate client command."""
        text = text.lower().strip()

        # Wake-word gating
        if self.listening_for_wake:
            if self.wake_word in text:
                self.listening_for_wake = False
                self.speak("At your service, sir.")
            return

        # Command intents
        if "system status" in text or "sysinfo" in text:
            await self.client.send("laptop", "sysinfo", {})
            self.speak("System status requested from your devices, sir.")

        elif "screenshot" in text:
            await self.client.send("laptop", "screenshot", {})
            self.speak("Capturing screenshot, sir.")

        elif "battery" in text:
            await self.client.send("phone", "battery", {})
            self.speak("Checking phone battery, sir.")

        elif "send" in text and "phone" in text:
            # Default demo file path — edit to suit your environment
            demo_path = os_path_demo()
            await self.client.send("phone", "file_transfer", {
                "action": "send",
                "path": demo_path,
                "target": "phone",
            })
            self.speak("Encrypted file transfer to phone initiated, sir.")

        elif "hello" in text or "jarvis" in text:
            self.speak("Yes, sir? How may I help?")

        elif "goodbye" in text or "sleep" in text:
            self.listening_for_wake = True
            self.speak("Standing by, sir.")

        else:
            self.speak("I'm not certain how to help with that, sir.")


def os_path_demo() -> str:
    """Return a demo file path that exists on the current OS, if any."""
    import os
    candidates = [
        os.path.expanduser("~/Documents/demo.pdf"),
        os.path.expanduser("~/Desktop/demo.pdf"),
        os.path.expanduser("~\\Documents\\demo.pdf"),
        os.path.expanduser("~\\Desktop\\demo.pdf"),
        "C:\\Users\\Public\\demo.pdf",
        "/tmp/demo.pdf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    # Fallback: return a placeholder so the command structure is visible
    return os.path.expanduser("~/Documents/demo.pdf")
