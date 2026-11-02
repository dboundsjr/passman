"""
Vault file format and I/O.

File layout on disk:
    [16 bytes: salt] [nonce + ciphertext+tag, from crypto_utils.encrypt()]

The salt is plaintext (not secret). Everything after it is opaque
encrypted bytes containing a JSON blob of all your saved entries.
"""

import json
import shutil
import os
import tempfile

from crypto_utils import generate_salt, derive_key, encrypt, decrypt, SALT_LENGTH


class VaultError(Exception):
    """Raised for vault-specific problems (missing file, wrong password, etc.)."""
    pass


def vault_exists(path: str) -> bool:
    return os.path.isfile(path)


def create_vault(path: str, master_password: str) -> None:
    """Create a brand-new, empty vault at `path`."""
    if vault_exists(path):
        raise VaultError(f"A vault already exists at {path}. Refusing to overwrite.")

    salt = generate_salt()
    key = derive_key(master_password, salt)

    empty_data = {}  # no entries yet
    plaintext = json.dumps(empty_data).encode("utf-8")
    encrypted_blob = encrypt(key, plaintext)

    _atomic_write(path, salt + encrypted_blob)


def unlock_vault(path: str, master_password: str) -> dict:
    """
    Open an existing vault and return its decrypted contents as a dict.
    Raises VaultError if the file doesn't exist, is corrupted, or the
    password is wrong.
    """
    if not vault_exists(path):
        raise VaultError(f"No vault found at {path}.")

    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError as e:
        # Covers things like the USB drive being unplugged mid-read.
        raise VaultError(f"Could not read vault file (is the drive connected?): {e}")

    if len(raw) < SALT_LENGTH:
        raise VaultError("Vault file is corrupted or truncated (too short).")

    salt = raw[:SALT_LENGTH]
    encrypted_blob = raw[SALT_LENGTH:]

    key = derive_key(master_password, salt)

    try:
        plaintext = decrypt(key, encrypted_blob)
    except Exception:
        # Wrong password AND tampering both land here, deliberately --
        # we don't want to tell an attacker which one it was.
        raise VaultError("Incorrect master password, or vault file is corrupted.")

    return json.loads(plaintext.decode("utf-8"))


def save_vault(path: str, master_password: str, data: dict) -> None:
    """
    Re-encrypt `data` and overwrite the vault at `path`.
    We re-derive the key rather than reusing an old one, and we
    generate a fresh salt on every save for simplicity and safety.
    """
    salt = generate_salt()
    key = derive_key(master_password, salt)

    plaintext = json.dumps(data).encode("utf-8")
    encrypted_blob = encrypt(key, plaintext)

    _atomic_write(path, salt + encrypted_blob)

def change_password(path: str, old_password: str, new_password: str) -> None:
    """
    Re-encrypt the vault under a new master password.

    Note this doesn't "edit" a stored password anywhere -- the master
    password was never stored to begin with. This unlocks with the old
    password (which also proves the caller actually knows it), then
    saves fresh: new salt, new derived key, full re-encryption of the
    existing data.
    """
    data = unlock_vault(path, old_password)  # raises VaultError if old_password is wrong
    save_vault(path, new_password, data)

def backup_vault(source_path: str, backup_path: str, overwrite: bool = False) -> None:
    """
    Copy the vault file (still fully encrypted) to a second location.
    This performs NO decryption -- it's a byte-for-byte copy, so it's
    exactly as secure as the original file, just duplicated.
    """
    if not vault_exists(source_path):
        raise VaultError(f"No vault found at {source_path}.")

    if vault_exists(backup_path) and not overwrite:
        raise VaultError(
            f"A file already exists at {backup_path}. Use --overwrite to replace it."
        )

    try:
        shutil.copy2(source_path, backup_path)
    except OSError as e:
        raise VaultError(f"Could not write backup (is the destination accessible?): {e}")

def _atomic_write(path: str, content: bytes) -> None:
    """
    Write `content` to `path` atomically: write to a temp file in the
    SAME directory first, then rename it into place. This avoids ever
    leaving a half-written, corrupted vault file if something goes
    wrong (USB unplugged, power loss, program crash) mid-write.
    """
    directory = os.path.dirname(os.path.abspath(path)) or "."
    try:
        fd, tmp_path = tempfile.mkstemp(dir=directory)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())  # force it out of OS buffers onto the physical disk
            os.replace(tmp_path, path)  # atomic on both Windows and POSIX
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise
    except OSError as e:
        raise VaultError(f"Could not write vault file (is the drive connected?): {e}")


if __name__ == "__main__":
    TEST_PATH = "test_vault.dat"

    # Clean slate for repeated test runs
    if os.path.exists(TEST_PATH):
        os.remove(TEST_PATH)

    print("Creating vault...")
    create_vault(TEST_PATH, "correct-horse-battery-staple")

    print("Unlocking with correct password...")
    data = unlock_vault(TEST_PATH, "correct-horse-battery-staple")
    print("Contents:", data)

    print("Adding an entry and saving...")
    data["github.com"] = {"username": "dboun", "password": "s3cr3t!"}
    save_vault(TEST_PATH, "correct-horse-battery-staple", data)

    print("Re-unlocking to confirm it persisted...")
    data2 = unlock_vault(TEST_PATH, "correct-horse-battery-staple")
    print("Contents:", data2)

    print("Trying wrong password...")
    try:
        unlock_vault(TEST_PATH, "wrong-password")
        print("ERROR: wrong password was accepted!")
    except VaultError as e:
        print("Correctly rejected:", e)

    os.remove(TEST_PATH)
    print("Test vault cleaned up.")