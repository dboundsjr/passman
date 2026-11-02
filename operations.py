"""
Vault entry operations.

These functions manipulate a plain dict (the decrypted vault contents)
in memory. They know nothing about encryption or file I/O -- that
separation keeps each layer simple and independently testable.
"""


class EntryError(Exception):
    """Raised for invalid entry operations (duplicate site, missing site, etc.)."""
    pass


def add_entry(data: dict, site: str, username: str, password: str, overwrite: bool = False) -> dict:
    """
    Add a new entry for `site`. Raises EntryError if the site already
    exists, unless overwrite=True is explicitly passed.
    """
    if not site:
        raise EntryError("Site name cannot be empty.")
    if not password:
        raise EntryError("Password cannot be empty.")

    if site in data and not overwrite:
        raise EntryError(f"An entry for '{site}' already exists. Use overwrite=True to replace it.")

    data[site] = {"username": username, "password": password}
    return data


def get_entry(data: dict, site: str) -> dict | None:
    """
    Look up a single entry by site name.
    Returns None if not found -- this is a normal, expected outcome,
    not an error condition, so we don't raise for it.
    """
    return data.get(site)


def list_entries(data: dict) -> list[str]:
    """
    Return just the site names in the vault, sorted alphabetically.
    Deliberately does NOT return usernames or passwords -- "list" should
    be safe to glance at without exposing secrets.
    """
    return sorted(data.keys())


def delete_entry(data: dict, site: str) -> bool:
    """
    Remove an entry. Returns True if something was deleted,
    False if the site didn't exist (so the caller can tell the
    difference and report it accurately).
    """
    if site in data:
        del data[site]
        return True
    return False


if __name__ == "__main__":
    vault_data = {}

    print("Adding github.com...")
    add_entry(vault_data, "github.com", "dboun", "s3cr3t!")

    print("Adding netflix.com...")
    add_entry(vault_data, "netflix.com", "dboun@email.com", "n3tfl1x!")

    print("Listing entries:", list_entries(vault_data))

    print("Getting github.com:", get_entry(vault_data, "github.com"))
    print("Getting a site that doesn't exist:", get_entry(vault_data, "doesnotexist.com"))

    print("Trying to add github.com again (should fail)...")
    try:
        add_entry(vault_data, "github.com", "dboun", "newpassword")
        print("ERROR: duplicate was allowed!")
    except EntryError as e:
        print("Correctly rejected:", e)

    print("Overwriting github.com explicitly...")
    add_entry(vault_data, "github.com", "dboun", "newpassword", overwrite=True)
    print("New value:", get_entry(vault_data, "github.com"))

    print("Deleting netflix.com...")
    deleted = delete_entry(vault_data, "netflix.com")
    print("Deleted?", deleted)
    print("Listing entries after delete:", list_entries(vault_data))

    print("Deleting netflix.com again (should be False this time)...")
    deleted_again = delete_entry(vault_data, "netflix.com")
    print("Deleted?", deleted_again)