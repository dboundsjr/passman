"""
Cryptographic core for the password manager.

Two responsibilities:
1. Key derivation: turn a master password into a 32-byte key (Argon2id).
2. Symmetric encryption: encrypt/decrypt data with that key (AES-256-GCM).
"""

import os
from argon2.low_level import hash_secret_raw, Type
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# --- Key derivation parameters ---
TIME_COST = 3
MEMORY_COST = 65536    # 64 MB
PARALLELISM = 4
KEY_LENGTH = 32         # 256-bit key
SALT_LENGTH = 16

# --- Encryption parameters ---
NONCE_LENGTH = 12       # 96 bits, the standard/recommended size for GCM


def generate_salt() -> bytes:
    """Generate a new random salt. Call this ONCE per vault, at creation time."""
    return os.urandom(SALT_LENGTH)


def derive_key(master_password: str, salt: bytes) -> bytes:
    """Derive a 32-byte encryption key from the master password + salt."""
    return hash_secret_raw(
        secret=master_password.encode("utf-8"),
        salt=salt,
        time_cost=TIME_COST,
        memory_cost=MEMORY_COST,
        parallelism=PARALLELISM,
        hash_len=KEY_LENGTH,
        type=Type.ID,
    )


def encrypt(key: bytes, plaintext: bytes) -> bytes:
    """
    Encrypt plaintext with AES-256-GCM.

    Generates a fresh random nonce for this call, and returns
    nonce + ciphertext (the auth tag is embedded in the ciphertext
    by the library automatically).
    """
    aesgcm = AESGCM(key)
    nonce = os.urandom(NONCE_LENGTH)
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data=None)
    return nonce + ciphertext


def decrypt(key: bytes, blob: bytes) -> bytes:
    """
    Decrypt a blob produced by encrypt().

    Raises cryptography.exceptions.InvalidTag if the key is wrong
    OR if the data was tampered with. Both cases look identical from
    the outside -- that's intentional, it doesn't leak which one happened.
    """
    aesgcm = AESGCM(key)
    nonce = blob[:NONCE_LENGTH]
    ciphertext = blob[NONCE_LENGTH:]
    return aesgcm.decrypt(nonce, ciphertext, associated_data=None)


if __name__ == "__main__":
    from cryptography.exceptions import InvalidTag

    salt = generate_salt()
    key = derive_key("hunter2", salt)

    secret_message = b"my_netflix_password_is_correcthorsebatterystaple"
    blob = encrypt(key, secret_message)
    print("Encrypted blob (hex):", blob.hex())

    recovered = decrypt(key, blob)
    print("Decrypted matches original?", recovered == secret_message)

    # Now let's prove tampering gets caught.
    tampered = bytearray(blob)
    tampered[-1] ^= 0xFF  # flip the last byte
    try:
        decrypt(key, bytes(tampered))
        print("Tampering was NOT detected -- this would be very bad!")
    except InvalidTag:
        print("Tampering correctly detected: decryption refused to return garbage.")

    # And prove a wrong key also fails cleanly.
    wrong_key = derive_key("wrong_password", salt)
    try:
        decrypt(wrong_key, blob)
        print("Wrong key was NOT detected -- this would be very bad!")
    except InvalidTag:
        print("Wrong key correctly rejected.")
