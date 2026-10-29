"""How confidential values are kept. Nothing a caller keys in is stored as readable digits.

- Secrets that are only ever checked (a PIN, a TPIN, a one-time password) are stored as a salted scrypt hash: slow to
  guess, and the same PIN never looks the same twice.
- Values the bank must look a customer up by (a phone code, a key code, an ID number) are stored as a keyed fingerprint
  (HMAC-SHA256 with the server's pepper), so a login can find its row without the table holding the number. Only the
  last four characters are kept beside it, for display.
"""

import hashlib
import hmac
import secrets

from .config import settings

# scrypt cost: 2**14 rounds, 8 blocks, 1 lane (the common interactive-login setting)
_N, _R, _P = 2**14, 8, 1


def hash_secret(value: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(str(value).encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${digest.hex()}"


def verify_secret(value: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, digest = stored.split("$")
        again = hashlib.scrypt(str(value).encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p), dklen=32)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(again.hex(), digest)


def fingerprint(value: str) -> str:
    """The keyed fingerprint a code or ID number is looked up by. Letters are compared without case."""
    return hmac.new(settings.pepper.encode(), str(value).strip().upper().encode(), hashlib.sha256).hexdigest()


def last4(value: str) -> str:
    return str(value)[-4:]
