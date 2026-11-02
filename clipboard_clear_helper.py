# """
# Standalone helper process for clearing the clipboard after a delay.

# This is launched as a fully independent process by passman.py, so it
# keeps running even after passman.py itself has already exited. It
# receives the password via stdin (not a command-line argument) so it
# never shows up in the process list or shell history.
# """

# import sys
# import time
# import pyperclip


# def main():
#     seconds = int(sys.argv[1])
#     original_text = sys.stdin.read()

#     time.sleep(seconds)

#     try:
#         # Only clear if the clipboard still holds what we put there --
#         # if the user copied something else in the meantime, leave it alone.
#         if pyperclip.paste() == original_text:
#             pyperclip.copy("")
#     except Exception:
#         pass  # best-effort; nothing more we can do if clipboard access fails


# if __name__ == "__main__":
#     main()  BELOW IS THE NEW CODE, STRICTLY FOR DEBUGGING PURPOSES. ABOVE IS THE ORIGINAL; THE CLIPBOARD CLEAR DID NOT FUNCTION AS EXPECTED, SO I REPLACED IT WITH THIS DEBUGGING VERSION. THE ORIGINAL IS COMMENTED OUT ABOVE.


# """
# Standalone helper process for clearing the clipboard after a delay.

# This is launched as a fully independent process by passman.py, so it
# keeps running even after passman.py itself has already exited. It
# receives the password via stdin (not a command-line argument) so it
# never shows up in the process list or shell history.
# """

# import sys
# import time
# import pyperclip

# LOG_PATH = "clipboard_helper_debug.log"


# def log(message: str) -> None:
#     with open(LOG_PATH, "a") as f:
#         f.write(message + "\n")


# def main():
#     log(f"Helper started. argv={sys.argv}")
#     seconds = int(sys.argv[1])
#     original_text = sys.stdin.read()
#     log(f"Read {len(original_text)} chars from stdin. Sleeping {seconds}s...")

#     time.sleep(seconds)
#     log("Woke up from sleep.")

#     try:
#         current = pyperclip.paste()
#         log(f"Current clipboard matches original? {current == original_text}")
#         if current == original_text:
#             pyperclip.copy("")
#             log("Cleared clipboard.")
#         else:
#             log("Did NOT clear -- clipboard contents differ from what we copied.")
#     except Exception as e:
#         log(f"EXCEPTION while clearing: {e!r}")


# if __name__ == "__main__":
#     main()
#     log("Helper exiting normally.") *BELOW IS THE FINAL CODE, WHICH SHOULDN'T CREATE A NEW WINDOW OR FORWARD ANYTHING TO A LOG FILE.*

"""
Standalone helper process for clearing the clipboard after a delay.

This is launched as a fully independent process by passman.py, so it
keeps running even after passman.py itself has already exited. It
receives the password via stdin (not a command-line argument) so it
never shows up in the process list or shell history.
"""

import sys
import time
import pyperclip


def main():
    seconds = int(sys.argv[1])
    original_text = sys.stdin.read()

    time.sleep(seconds)

    try:
        # Only clear if the clipboard still holds what we put there --
        # if the user copied something else in the meantime, leave it alone.
        if pyperclip.paste() == original_text:
            pyperclip.copy("")
    except Exception:
        pass  # best-effort; nothing more we can do if clipboard access fails


if __name__ == "__main__":
    main()