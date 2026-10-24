# =============================================================================
# J.A.R.V.I.S. Mk.II — End-to-End Encryption Module
# =============================================================================
# X25519 key exchange + AES-256-GCM authenticated encryption.
# Provides Perfect Forward Secrecy for file transfers between devices.
# =============================================================================

import os
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class EncryptionManager:
    def __init__(self):
        self.session_keys: dict = {}

    def generate_keypair(self):
        """Generate an ephemeral X25519 keypair."""
        private = X25519PrivateKey.generate()
        public = private.public_key()
        return private, public

    def serialize_public(self, public_key):
        """Serialize a public key to raw 32 bytes."""
        return public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

    def deserialize_public(self, raw):
        """Deserialize raw 32 bytes into an X25519PublicKey."""
        return X25519PublicKey.from_public_bytes(raw)

    def derive_shared_key(self, private_key, peer_public_raw):
        """Perform X25519 key exchange and derive an AESGCM key via HKDF-SHA256."""
        peer_public = self.deserialize_public(peer_public_raw)
        shared = private_key.exchange(peer_public)
        derived = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"jarvis-file-transfer-v1",
        ).derive(shared)
        return AESGCM(derived)

    def encrypt(self, key: AESGCM, plaintext: bytes, associated_data: bytes = b""):
        """Encrypt plaintext with AES-256-GCM. Returns nonce + ciphertext."""
        nonce = os.urandom(12)
        ct = key.encrypt(nonce, plaintext, associated_data)
        return nonce + ct

    def decrypt(self, key: AESGCM, payload: bytes, associated_data: bytes = b""):
        """Decrypt nonce + ciphertext with AES-256-GCM. Returns plaintext."""
        nonce = payload[:12]
        ct = payload[12:]
        return key.decrypt(nonce, ct, associated_data)
