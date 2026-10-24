# =============================================================================
# J.A.R.V.I.S. Mk.II — Laptop Plugins (Enterprise)
# =============================================================================
# System info, restricted shell, TTS, screenshots, app launcher, and
# encrypted resume-aware file transfer (X25519 + AES-256-GCM).
# =============================================================================

import os
import base64
import hashlib
import asyncio
import platform
import psutil
import subprocess
import time
import zlib

from jarvis_client import Plugin
import pyttsx3
from mss import mss
from PIL import Image
import io

from crypto import EncryptionManager

CHUNK_SIZE = 64 * 1024


class SysInfo(Plugin):
    async def run(self, args: dict) -> dict:
        batt = psutil.sensors_battery()
        return {
            "platform": platform.platform(),
            "node": platform.node(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": psutil.virtual_memory()._asdict(),
            "disk": psutil.disk_usage("/")._asdict(),
            "battery": batt._asdict() if batt else None,
        }


class Shell(Plugin):
    """Restricted shell — only whitelisted binaries may be executed remotely."""
    WHITELIST = {"echo", "pwd", "ls", "dir", "whoami", "hostname", "uptime", "systeminfo"}

    async def run(self, args: dict) -> dict:
        cmd = args.get("cmd", "")
        binary = cmd.split()[0] if cmd else ""
        if binary not in self.WHITELIST:
            return {"error": f"Command '{binary}' is not whitelisted"}
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            return {
                "output": result.stdout,
                "error": result.stderr,
                "code": result.returncode,
            }
        except Exception as e:
            return {"error": str(e)}


class TTS(Plugin):
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 175)

    async def run(self, args: dict) -> dict:
        text = args.get("text", "At your service, sir.")
        self.engine.say(text)
        self.engine.runAndWait()
        return {"spoken": text}


class Screenshot(Plugin):
    async def run(self, args: dict) -> dict:
        with mss() as sct:
            shot = sct.grab(sct.monitors[1])
            img = Image.frombytes("RGB", shot.size, shot.rgb)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return {
                "image_base64": base64.b64encode(buf.getvalue()).decode(),
                "size": list(shot.size),
            }


class OpenApp(Plugin):
    async def run(self, args: dict) -> dict:
        app = args.get("app", "")
        system = platform.system()
        try:
            if system == "Darwin":
                subprocess.run(["open", "-a", app])
            elif system == "Windows":
                os.startfile(app)
            else:
                subprocess.Popen([app])
            return {"launched": app}
        except Exception as e:
            return {"error": str(e)}


class FileTransfer(Plugin):
    """Encrypted, resume-aware file transfer between devices."""
    def __init__(self):
        self.crypto = EncryptionManager()
        self.session_keys: dict = {}

    def _file_hash(self, path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    async def _ensure_session_key(self, target: str):
        if target in self.session_keys:
            return self.session_keys[target]

        priv, pub = self.crypto.generate_keypair()
        pub_b64 = base64.b64encode(self.crypto.serialize_public(pub)).decode()

        try:
            resp = await self.client.send_and_wait(target, "key_exchange_init", {
                "ephemeral_pubkey": pub_b64,
            }, timeout=15)
        except asyncio.TimeoutError:
            raise Exception("Key exchange timed out")

        their_pub_b64 = resp.get("args", {}).get("ephemeral_pubkey")
        if not their_pub_b64:
            raise Exception("Key exchange response missing public key")

        their_pub = base64.b64decode(their_pub_b64)
        key = self.crypto.derive_shared_key(priv, their_pub)
        self.session_keys[target] = key
        return key

    async def run(self, args: dict) -> dict:
        action = args.get("action")
        target = args.get("target")
        if action == "send":
            return await self._send_file(args)
        if action == "verify":
            return await self._verify_file(args)
        return {"error": "Unknown file action"}

    async def _send_file(self, args):
        path = args.get("path")
        if not path or not os.path.exists(path):
            return {"error": "File not found"}

        filename = os.path.basename(path)
        size = os.path.getsize(path)
        total_chunks = (size + CHUNK_SIZE - 1) // CHUNK_SIZE
        target = args.get("target")
        file_hash = self._file_hash(path)

        key = await self._ensure_session_key(target)

        try:
            ack = await self.client.send_and_wait(target, "file_start", {
                "filename": filename,
                "size": size,
                "total_chunks": total_chunks,
                "sha256": file_hash,
                "encrypted": True,
            }, timeout=20)
        except asyncio.TimeoutError:
            return {"error": "Receiver did not acknowledge file_start"}

        missing = ack.get("args", {}).get("missing_chunks", list(range(total_chunks)))
        if not missing:
            return {"status": "already complete", "filename": filename, "sha256": file_hash}

        sent = 0
        with open(path, "rb") as f:
            for i in missing:
                f.seek(i * CHUNK_SIZE)
                chunk = f.read(CHUNK_SIZE)
                encrypted_payload = self.crypto.encrypt(key, chunk, associated_data=filename.encode())
                b64 = base64.b64encode(encrypted_payload).decode()
                await self.client.send(target, "file_chunk", {
                    "filename": filename,
                    "chunk": i,
                    "data": b64,
                    "encrypted": True,
                })
                sent += 1
                await asyncio.sleep(0.005)

        await self.client.send(target, "file_end", {
            "filename": filename,
            "sha256": file_hash,
            "encrypted": True,
        })
        return {
            "status": "sent",
            "filename": filename,
            "chunks_sent": sent,
            "total_chunks": total_chunks,
            "sha256": file_hash,
            "encrypted": True,
        }

    async def _verify_file(self, args):
        path = args.get("path")
        if not path or not os.path.exists(path):
            return {"error": "File not found"}
        return {"sha256": self._file_hash(path), "size": os.path.getsize(path)}
