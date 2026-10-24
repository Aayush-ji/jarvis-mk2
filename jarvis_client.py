# =============================================================================
# J.A.R.V.I.S. Mk.II — Base Client Core
# =============================================================================
# Provides the persistent WebSocket connection to the relay server,
# plugin execution, encrypted message routing, and resume-aware acknowledgements.
# =============================================================================

import asyncio
import json
import time
import uuid
from typing import Dict, Any, Optional
from dataclasses import dataclass
import websockets


@dataclass
class JarvisConfig:
    device_id: str
    token: str
    server_url: str
    name: str = "JARVIS Client"
    max_reconnect_delay: int = 60


class Plugin:
    """Base class for JARVIS plugins. The client injects itself as .client."""
    client: Optional["JarvisClient"] = None

    async def run(self, args: dict) -> dict:
        return {"error": "not implemented"}


class JarvisClient:
    def __init__(self, config: JarvisConfig):
        self.config = config
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.running = True
        self.plugins: Dict[str, Plugin] = {}
        self.pending_acks: Dict[str, asyncio.Future] = {}
        self.reconnect_delay = 2
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def register(self, name: str, plugin: Plugin):
        self.plugins[name] = plugin
        plugin.client = self
        print(f"[{self.config.name}] Plugin loaded: {name}")

    async def execute(self, command: str, args: dict) -> dict:
        try:
            if command in self.plugins:
                plugin = self.plugins[command]
                plugin.client = self
                return await plugin.run(args)
            return {"error": f"Unknown command: {command}"}
        except Exception as e:
            return {"error": str(e)}

    async def send(self, target: str, command: str, args: dict = {}):
        if self.ws:
            await self.ws.send_json({
                "target": target,
                "command": command,
                "args": args,
            })

    async def send_and_wait(self, target: str, command: str, args: dict, timeout: int = 30):
        """Send a command and wait for a specific acknowledgement (used for resume handshake)."""
        tid = args.get("transfer_id") or str(uuid.uuid4())
        args["transfer_id"] = tid
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self.pending_acks[tid] = fut
        await self.send(target, command, args)
        try:
            return await asyncio.wait_for(fut, timeout)
        except asyncio.TimeoutError:
            self.pending_acks.pop(tid, None)
            raise

    async def _heartbeat(self, ws):
        while self.running:
            await asyncio.sleep(30)
            try:
                await ws.ping()
            except Exception:
                break

    async def connect(self):
        """Main connection loop with exponential backoff reconnection."""
        uri = f"{self.config.server_url}/{self.config.device_id}?token={self.config.token}"
        self.loop = asyncio.get_running_loop()

        while self.running:
            try:
                async with websockets.connect(uri, ping_interval=20, ping_timeout=10) as ws:
                    self.ws = ws
                    self.reconnect_delay = 2
                    self.heartbeat_task = asyncio.create_task(self._heartbeat(ws))
                    print(f"[{self.config.name}] Online at {time.strftime('%H:%M:%S')}")
                    await self._handle(ws)
            except Exception as e:
                print(f"[{self.config.name}] Connection lost ({e}). Reconnecting in {self.reconnect_delay}s...")
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, self.config.max_reconnect_delay)
            finally:
                if self.heartbeat_task:
                    self.heartbeat_task.cancel()
                self.ws = None

    async def _handle(self, ws):
        async for message in ws:
            data = json.loads(message)
            cmd = data.get("command")
            args = data.get("args", {})

            # Intercept transfer acknowledgements so send_and_wait can resolve them
            if cmd in ("file_ack", "file_complete", "transfer_resume", "key_exchange_response"):
                tid = args.get("transfer_id")
                if tid and tid in self.pending_acks:
                    fut = self.pending_acks.pop(tid)
                    if not fut.done():
                        fut.set_result(data)
                continue

            print(f"\n[{self.config.name}] ← {data.get('from')}: {cmd}")
            result = await self.execute(cmd, args)
            if self.ws:
                await self.ws.send_json({
                    "response_to": cmd,
                    "result": result,
                    "from": self.config.device_id,
                    "ts": time.time(),
                })
