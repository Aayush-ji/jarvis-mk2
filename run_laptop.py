# =============================================================================
# J.A.R.V.I.S. Mk.II — Laptop Agent Entry Point
# =============================================================================
# Runs the desktop agent: connects to the relay, loads plugins, and bridges
# voice commands to encrypted device-to-device actions.
# =============================================================================

import asyncio
import os
import sys
import threading
from dotenv import load_dotenv

from jarvis_client import JarvisClient, JarvisConfig
from laptop_plugins import (
    SysInfo, Shell, TTS, Screenshot, OpenApp, FileTransfer
)
from voice_interface import JarvisVoice


def start_voice_thread(client: JarvisClient, voice: JarvisVoice, loop: asyncio.AbstractEventLoop):
    """Voice input loop — microphone if PyAudio available, otherwise keyboard demo mode."""
    if voice.microphone is not None:
        print("[JARVIS] Voice interface thread started. Say 'Hey Jarvis' to wake.")
        while client.running:
            try:
                text = voice.listen()
                if text:
                    print(f"[JARVIS] Heard: {text}")
                    asyncio.run_coroutine_threadsafe(voice.handle_voice(text), loop)
            except Exception as e:
                print(f"[JARVIS] Voice thread error: {e}")
            import time as _time
            _time.sleep(0.3)
    else:
        print("[JARVIS] Keyboard demo mode active. Type commands below (no microphone).")
        print("[JARVIS] Examples: 'hey jarvis', 'system status', 'screenshot', 'battery', 'goodbye'")
        while client.running:
            try:
                text = input("> ")
                if text:
                    print(f"[JARVIS] Typed: {text}")
                    asyncio.run_coroutine_threadsafe(voice.handle_voice(text), loop)
            except (EOFError, KeyboardInterrupt):
                break
            except Exception as e:
                print(f"[JARVIS] Input error: {e}")


async def main():
    load_dotenv()

    device_id = os.getenv("LAPTOP_DEVICE_ID", "laptop")
    token = os.getenv("LAPTOP_TOKEN", "")
    server_url = os.getenv("SERVER_URL", "ws://localhost:8765")

    if not token:
        print("[JARVIS] FATAL: LAPTOP_TOKEN not found in .env")
        print("[JARVIS] Enroll the device first: POST /auth/enroll on the relay server.")
        sys.exit(1)

    config = JarvisConfig(
        device_id=device_id,
        token=token,
        server_url=server_url,
        name="Laptop",
    )

    client = JarvisClient(config)

    # Register core plugins
    client.register("sysinfo", SysInfo())
    client.register("shell", Shell())
    client.register("say", TTS())
    client.register("screenshot", Screenshot())
    client.register("open", OpenApp())
    client.register("file_transfer", FileTransfer())

    # Initialise voice interface
    voice = JarvisVoice(client)

    # Start voice recognition in a background thread
    voice_thread = threading.Thread(
        target=start_voice_thread,
        args=(client, voice, client.loop or asyncio.get_running_loop()),
        daemon=True,
    )
    voice_thread.start()

    print(f"[JARVIS] {config.name} agent initialised.")
    print(f"[JARVIS] Connecting to {server_url}...")

    # Main connection loop (blocks until shutdown)
    await client.connect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[JARVIS] Shutting down, sir.")
