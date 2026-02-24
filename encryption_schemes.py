import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305

def _nonce() -> bytes:
    return os.urandom(12)

def aesgcm_encrypt(key: bytes, plaintext: bytes, aad: bytes = b"") -> tuple[bytes, bytes]:
    aesgcm = AESGCM(key)
    n = _nonce()
    ct = aesgcm.encrypt(n, plaintext, aad)
    return n, ct

def aesgcm_decrypt(key: bytes, nonce: bytes, ciphertext: bytes, aad: bytes = b"") -> bytes:
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, aad)

def chacha_encrypt(key: bytes, plaintext: bytes, aad: bytes = b"") -> tuple[bytes, bytes]:
    chacha = ChaCha20Poly1305(key)
    n = _nonce()
    ct = chacha.encrypt(n, plaintext, aad)
    return n, ct

def chacha_decrypt(key: bytes, nonce: bytes, ciphertext: bytes, aad: bytes = b"") -> bytes:
    chacha = ChaCha20Poly1305(key)
    return chacha.decrypt(nonce, ciphertext, aad)
