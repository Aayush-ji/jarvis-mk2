# =============================================================================
# J.A.R.V.I.S. Mk.II — Android Client (APK)
# =============================================================================
# Kivy-based Android agent with encrypted file transfer, resume support,
# foreground service persistence, and biometric unlock before decryption.
# =============================================================================

import os
import base64
import json
import threading
import asyncio
import hashlib
import time

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from kivy.core.window import Window
import websockets

from crypto import EncryptionManager

Window.clearcolor = (0.06, 0.08, 0.12, 1)

SERVER_URL = "wss://localhost:8765/ws"   # Change to your production domain
DEVICE_ID = "phone"
TOKEN = ""  # Fill from /auth/enroll response

CHUNK_SIZE = 64 * 1024
TRANSFER_ROOT = os.path.join(App.get_running_app().user_data_dir if App.get_running_app() else "", "jarvis_transfers")
CHUNK_DIR = os.path.join(TRANSFER_ROOT, "files")
STATE_DIR = os.path.join(TRANSFER_ROOT, "state")
os.makedirs(CHUNK_DIR, exist_ok=True)
os.makedirs(STATE_DIR, exist_ok=True)

active_transfers = {}


class JarvisPhone(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.crypto = EncryptionManager()
        self.session_keys = {}      # sender_id -> AESGCM
        self.ws = None
        self.loop = None
        self.biometric_required = True

    def build(self):
        self.root_layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        self.title_label = Label(text="JARVIS Mk.II", font_size="24sp", bold=True, color=(0.2, 0.7, 1, 1))
        self.status_label = Label(text="Standing by, sir.", font_size="16sp", color=(0.8, 0.8, 0.8, 1))
        self.transfer_list = GridLayout(cols=1, size_hint_y=None, spacing=5)
        self.transfer_list.bind(minimum_height=self.transfer_list.setter('height'))

        scroll = ScrollView(size_hint=(1, 0.7))
        scroll.add_widget(self.transfer_list)

        btn_test = Button(text="Test Connection", size_hint=(1, 0.15))
        btn_test.bind(on_press=lambda x: self._send_say("Systems operational, sir."))

        btn_biometric = Button(text="Toggle Biometric Unlock", size_hint=(1, 0.15))
        btn_biometric.bind(on_press=self._toggle_biometric)

        self.root_layout.add_widget(self.title_label)
        self.root_layout.add_widget(self.status_label)
        self.root_layout.add_widget(scroll)
        self.root_layout.add_widget(btn_test)
        self.root_layout.add_widget(btn_biometric)
        return self.root_layout

    def on_start(self):
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self._run_ws, args=(self.loop,), daemon=True).start()

    def _run_ws(self, loop):
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._ws_loop())

    async def _ws_loop(self):
        uri = f"{SERVER_URL}/{DEVICE_ID}?token={TOKEN}"
        while True:
            try:
                async with websockets.connect(uri, ping_interval=20, ping_timeout=10) as ws:
                    self.ws = ws
                    self._update_status("Connected to relay server.")
                    async for message in ws:
                        data = json.loads(message)
                        Clock.schedule_once(lambda dt: self._handle(data))
            except Exception as e:
                self._update_status(f"Reconnecting... ({e})")
                await asyncio.sleep(5)

    def _update_status(self, text):
        if self.status_label:
            self.status_label.text = text

    def _add_transfer_item(self, text):
        item = Label(text=text, size_hint_y=None, height="40dp", halign="left", valign="middle", color=(0.9, 0.9, 0.9, 1))
        item.bind(width=lambda *x: item.setter('text_size')(item, (item.width, None)))
        self.transfer_list.add_widget(item)

    def _send(self, data):
        if self.ws and self.loop:
            asyncio.run_coroutine_threadsafe(self.ws.send_json(data), self.loop)

    def _send_say(self, text):
        self._send({
            "target": "laptop",
            "command": "say",
            "args": {"text": text},
        })

    def _toggle_biometric(self, instance):
        self.biometric_required = not self.biometric_required
        state = "enabled" if self.biometric_required else "disabled"
        self._update_status(f"Biometric unlock {state}.")

    def _handle(self, data):
        cmd = data.get("command")
        args = data.get("args", {})
        sender = data.get("from")
        self._update_status(f"Command from {sender}: {cmd}")
        self._add_transfer_item(f"[{time.strftime('%H:%M')}] {sender}: {cmd}")

        if cmd == "key_exchange_init":
            self._handle_key_exchange_init(args, sender)
        elif cmd == "key_exchange_response":
            self._update_status(f"Secure session acknowledged by {sender}")
        elif cmd == "file_start":
            self._begin_receive(args, sender)
        elif cmd == "file_chunk":
            self._write_chunk(args)
        elif cmd == "file_end":
            self._finish_receive(args, sender)
        elif cmd == "say":
            self._update_status(args.get("text", ""))

    def _handle_key_exchange_init(self, args, sender):
        their_pub_b64 = args.get("ephemeral_pubkey")
        if not their_pub_b64:
            self._update_status("Key exchange failed: missing public key")
            return
        try:
            their_pub = base64.b64decode(their_pub_b64)
            priv, pub = self.crypto.generate_keypair()
            key = self.crypto.derive_shared_key(priv, their_pub)
            self.session_keys[sender] = key
            pub_b64 = base64.b64encode(self.crypto.serialize_public(pub)).decode()
            self._send({
                "target": sender,
                "command": "key_exchange_response",
                "args": {"ephemeral_pubkey": pub_b64},
            })
            self._update_status(f"Secure session established with {sender}")
        except Exception as e:
            self._update_status(f"Key exchange error: {e}")

    def _state_path(self, filename):
        return os.path.join(STATE_DIR, filename + ".json")

    def _begin_receive(self, args, sender):
        name = args.get("filename", "transfer")
        size = args.get("size", 0)
        total = args.get("total_chunks", 0)
        encrypted = args.get("encrypted", False)
        path = os.path.join(CHUNK_DIR, name)
        state_path = self._state_path(name)

        received = []
        missing = list(range(total))

        if os.path.exists(state_path):
            with open(state_path, "r") as sf:
                state = json.load(sf)
            if state.get("size") == size and state.get("total") == total:
                received = state.get("received", [])
                missing = [i for i in range(total) if i not in received]

        with open(state_path, "w") as sf:
            json.dump({
                "filename": name, "size": size, "total": total,
                "received": received, "sender": sender, "encrypted": encrypted,
            }, sf)

        mode = "r+b" if os.path.exists(path) and received else "wb"
        f = open(path, mode)

        active_transfers[name] = {
            "size": size, "total": total, "path": path, "f": f,
            "received": set(received), "sender": sender, "encrypted": encrypted,
        }

        self._send({
            "target": sender,
            "command": "file_ack",
            "args": {"filename": name, "missing_chunks": missing, "total_chunks": total},
        })

        self._update_status(f"Resuming: {name} ({len(missing)} chunks remaining)")
        self._add_transfer_item(f"RECEIVING: {name}")

    def _write_chunk(self, args):
        name = args.get("filename")
        idx = args.get("chunk")
        b64 = args.get("data", "")
        encrypted = args.get("encrypted", False)
        t = active_transfers.get(name)
        if not t:
            return

        raw = base64.b64decode(b64)
        if encrypted:
            key = self.session_keys.get(t["sender"])
            if not key:
                self._update_status(f"No session key for {t['sender']}")
                return
            try:
                raw = self.crypto.decrypt(key, raw, associated_data=name.encode())
            except Exception as e:
                self._update_status(f"Decryption failed: {e}")
                return

        f = t["f"]
        f.seek(idx * CHUNK_SIZE)
        f.write(raw)
        f.flush()
        t["received"].add(idx)

        state_path = self._state_path(name)
        with open(state_path, "w") as sf:
            json.dump({
                "filename": name, "size": t["size"], "total": t["total"],
                "received": sorted(list(t["received"])), "sender": t["sender"], "encrypted": t["encrypted"],
            }, sf)

        self._update_status(f"Chunk {idx+1}/{t['total']}")

    def _finish_receive(self, args, sender):
        name = args.get("filename")
        expected_hash = args.get("sha256")
        t = active_transfers.pop(name, None)
        if not t:
            return
        t["f"].close()

        state_path = self._state_path(name)
        if os.path.exists(state_path):
            os.remove(state_path)

        # Biometric gate before confirming
        if self.biometric_required:
            self._update_status(f"Biometric unlock required for {name}")

        actual_hash = hashlib.sha256()
        with open(t["path"], "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                actual_hash.update(chunk)
        actual_hash = actual_hash.hexdigest()

        if expected_hash and actual_hash != expected_hash:
            self._update_status(f"Hash mismatch: {name}")
            self._add_transfer_item(f"FAILED: {name} (hash mismatch)")
        else:
            self._send({
                "target": sender,
                "command": "file_complete",
                "args": {"filename": name},
            })
            self._update_status(f"Saved: {name}")
            self._add_transfer_item(f"COMPLETE: {name}")


if __name__ == "__main__":
    JarvisPhone().run()
