"""
passman - a local encrypted password manager.

Usage:
    python passman.py --vault <path> init
    python passman.py --vault <path> add <site> [username] [--generate]
    python passman.py --vault <path> get <site>
    python passman.py --vault <path> list
    python passman.py --vault <path> delete <site>
"""

import argparse
import getpass
import os
import secrets
import string
import subprocess
import sys

import pyperclip

from vault import create_vault, unlock_vault, save_vault, change_password, backup_vault, VaultError
from operations import add_entry, get_entry, list_entries, delete_entry, EntryError

CLIPBOARD_CLEAR_SECONDS = 20
HELPER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clipboard_clear_helper.py")


def prompt_master_password(confirm: bool = False) -> str:
    """
    Prompt for the master password without echoing it to the screen.
    If confirm=True, ask twice and make sure they match (used on vault creation).
    """
    password = getpass.getpass("Master password: ")
    if confirm:
        again = getpass.getpass("Confirm master password: ")
        if password != again:
            print("Passwords did not match.", file=sys.stderr)
            sys.exit(1)
    return password


def generate_password(length: int = 20) -> str:
    """
    Generate a strong random password using Python's `secrets` module,
    which is built for security-sensitive randomness (unlike the plain
    `random` module, which is predictable and NOT safe for this).
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    return "".join(secrets.choice(alphabet) for _ in range(length))

def cmd_change_password(args):
    old_password = getpass.getpass("Current master password: ")
    new_password = getpass.getpass("New master password: ")
    new_password_confirm = getpass.getpass("Confirm new master password: ")

    if new_password != new_password_confirm:
        print("New passwords did not match.", file=sys.stderr)
        sys.exit(1)

    try:
        change_password(args.vault, old_password, new_password)
    except VaultError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print("Master password changed.")

# def copy_with_auto_clear(text: str, seconds: int = CLIPBOARD_CLEAR_SECONDS) -> None:
#     """
#     Copy `text` to the clipboard, then launch a fully independent
#     background process to clear it after `seconds`. Unlike a thread,
#     this process keeps running even after passman.py itself exits --
#     so the terminal gets control back immediately, but the clipboard
#     still gets wiped a moment later.
#     """
#     try:
#         pyperclip.copy(text)
#     except Exception:
#         print("(Could not access clipboard; printing password instead.)")
#         print(text)
#         return

#     print(f"Password copied to clipboard. It will clear automatically in {seconds} seconds.")

#     # Platform-specific flags so the child process is fully detached from
#     # this one -- it survives after we exit, rather than being tied to us.
#     kwargs = {}
#     if sys.platform == "win32":
#         DETACHED_PROCESS = 0x00000008
#         CREATE_NEW_PROCESS_GROUP = 0x00000200
#         kwargs["creationflags"] = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
#     else:
#         kwargs["start_new_session"] = True  # detach on Linux/macOS

#     proc = subprocess.Popen(
#         [sys.executable, HELPER_SCRIPT, str(seconds)],
#         stdin=subprocess.PIPE,
#         stdout=subprocess.DEVNULL,
#         stderr=subprocess.DEVNULL,
#         close_fds=True,
#         **kwargs,
#     )
#     # Send the password over stdin (not as a command-line argument) so it
#     # never appears in the process list or shell history.
#     proc.stdin.write(text.encode("utf-8"))
#     proc.stdin.close()  *THIS HAD TO BE REPLACED DUE TO THE HELPER PROCESS CREATING A NEW WINDOW (BELOW IS THE NEW CALL)*

def copy_with_auto_clear(text: str, seconds: int = CLIPBOARD_CLEAR_SECONDS) -> None:
    """
    Copy `text` to the clipboard, then launch a fully independent
    background process to clear it after `seconds`. Unlike a thread,
    this process keeps running even after passman.py itself exits --
    so the terminal gets control back immediately, but the clipboard
    still gets wiped a moment later.
    """
    try:
        pyperclip.copy(text)
    except Exception:
        print("(Could not access clipboard; printing password instead.)")
        print(text)
        return

    print(f"Password copied to clipboard. It will clear automatically in {seconds} seconds.")

    # Platform-specific flags so the child process is fully detached from
    # this one, AND doesn't flash a visible console window.
    kwargs = {}
    if sys.platform == "win32":
        CREATE_NO_WINDOW = 0x08000000
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        kwargs["creationflags"] = CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP

        # Prefer pythonw.exe (the windowless variant of the interpreter)
        # over python.exe -- it has no console attached at all, so there's
        # nothing to flash even briefly.
        pythonw = sys.executable.replace("python.exe", "pythonw.exe")
        interpreter = pythonw if os.path.exists(pythonw) else sys.executable
    else:
        kwargs["start_new_session"] = True  # detach on Linux/macOS
        interpreter = sys.executable

    proc = subprocess.Popen(
        [interpreter, HELPER_SCRIPT, str(seconds)],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        **kwargs,
    )
    # Send the password over stdin (not as a command-line argument) so it
    # never appears in the process list or shell history.
    proc.stdin.write(text.encode("utf-8"))
    proc.stdin.close()


def cmd_init(args):
    master_password = prompt_master_password(confirm=True)
    try:
        create_vault(args.vault, master_password)
    except VaultError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"Vault created at {args.vault}")


def cmd_add(args):
    master_password = prompt_master_password()
    try:
        data = unlock_vault(args.vault, master_password)
    except VaultError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.generate:
        password = generate_password()
        print(f"Generated password: {password}")
    else:
        password = getpass.getpass("Password for this entry: ")

    try:
        add_entry(data, args.site, args.username or "", password, overwrite=args.overwrite)
    except EntryError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    save_vault(args.vault, master_password, data)
    print(f"Saved entry for {args.site}")


def cmd_get(args):
    master_password = prompt_master_password()
    try:
        data = unlock_vault(args.vault, master_password)
    except VaultError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    entry = get_entry(data, args.site)
    if entry is None:
        print(f"No entry found for {args.site}", file=sys.stderr)
        sys.exit(1)

    print(f"Username: {entry['username']}")
    copy_with_auto_clear(entry["password"])


def cmd_list(args):
    master_password = prompt_master_password()
    try:
        data = unlock_vault(args.vault, master_password)
    except VaultError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    sites = list_entries(data)
    if not sites:
        print("(vault is empty)")
    else:
        for site in sites:
            print(site)


def cmd_delete(args):
    master_password = prompt_master_password()
    try:
        data = unlock_vault(args.vault, master_password)
    except VaultError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    deleted = delete_entry(data, args.site)
    if not deleted:
        print(f"No entry found for {args.site}", file=sys.stderr)
        sys.exit(1)

    save_vault(args.vault, master_password, data)
    print(f"Deleted entry for {args.site}")

def cmd_backup(args):
    try:
        backup_vault(args.vault, args.backup_path, overwrite=args.overwrite)
    except VaultError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"Backed up vault to {args.backup_path}")

def build_parser():
    parser = argparse.ArgumentParser(description="A local encrypted password manager.")
    parser.add_argument("--vault", required=True, help="Path to the vault file (e.g. E:\\vault.dat)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Create a new vault").set_defaults(func=cmd_init)

    add_parser = subparsers.add_parser("add", help="Add a new entry")
    add_parser.add_argument("site", help="Site or service name, e.g. github.com")
    add_parser.add_argument("username", nargs="?", default="", help="Username for this entry")
    add_parser.add_argument("--generate", action="store_true", help="Generate a strong random password")
    add_parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing entry")
    add_parser.set_defaults(func=cmd_add)

    get_parser = subparsers.add_parser("get", help="Retrieve an entry")
    get_parser.add_argument("site")
    get_parser.set_defaults(func=cmd_get)

    subparsers.add_parser("list", help="List all site names in the vault").set_defaults(func=cmd_list)

    delete_parser = subparsers.add_parser("delete", help="Delete an entry")
    delete_parser.add_argument("site")
    delete_parser.set_defaults(func=cmd_delete)
    
    subparsers.add_parser(
        "change-password", help="Change the vault's master password"
    ).set_defaults(func=cmd_change_password)

    backup_parser = subparsers.add_parser("backup", help="Copy the vault to a backup location")
    backup_parser.add_argument("backup_path", help="Where to save the backup copy")
    backup_parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing backup file")
    backup_parser.set_defaults(func=cmd_backup)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()