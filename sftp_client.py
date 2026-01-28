from __future__ import annotations

from pathlib import Path
import socket
import time
import paramiko

from config import (
    SFTP_ENABLED,
    SFTP_HOST,
    SFTP_PORT,
    SFTP_USERNAME,
    SFTP_PRIVATE_KEY_PATH,
    SFTP_REMOTE_BASE_DIR,
)

# Reasonable defaults for flaky SFTP connections
CONNECT_TIMEOUT_SECONDS = 20
SOCKET_TIMEOUT_SECONDS = 30
KEEPALIVE_SECONDS = 30
RETRY_ONCE = True


def _as_bool(val) -> bool:
    """Parse typical env/ini boolean shapes safely."""
    if isinstance(val, bool):
        return val
    if val is None:
        return False
    s = str(val).strip().lower()
    return s in ("1", "true", "yes", "y", "on")


class SFTPClient:
    def __init__(self):
        # IMPORTANT: SFTP_ENABLED may be a string from .env; parse it.
        self.enabled = _as_bool(SFTP_ENABLED)
        self.transport = None
        self.sftp = None
        self._key = None
        self._connected = False

    def _load_key(self):
        key_path = Path(SFTP_PRIVATE_KEY_PATH)

        if not key_path.exists():
            raise FileNotFoundError(f"SFTP private key not found: {key_path}")
        if not key_path.is_file():
            raise ValueError(f"SFTP private key path is not a file: {key_path}")

        key = None
        last_error = None

        for key_cls in (paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey):
            try:
                key = key_cls.from_private_key_file(str(key_path))
                break
            except Exception as exc:
                last_error = exc

        if key is None:
            raise ValueError(
                "Unsupported or invalid SSH private key.\n"
                f"Path: {key_path}\n"
                f"Last error: {last_error}"
            )

        self._key = key

    def connect(self):
        if not self.enabled:
            return

        if self._connected and self.transport and self.transport.is_active() and self.sftp:
            return

        if self._key is None:
            self._load_key()

        # Clean up stale handles
        self.close()

        # Create transport with timeout + keepalive
        self.transport = paramiko.Transport((SFTP_HOST, int(SFTP_PORT)))
        self.transport.banner_timeout = CONNECT_TIMEOUT_SECONDS
        self.transport.auth_timeout = CONNECT_TIMEOUT_SECONDS
        self.transport.set_keepalive(KEEPALIVE_SECONDS)

        self.transport.connect(username=SFTP_USERNAME, pkey=self._key)

        self.sftp = paramiko.SFTPClient.from_transport(self.transport)

        # Ensure the underlying channel/socket won’t block forever
        try:
            chan = self.sftp.get_channel()
            chan.settimeout(SOCKET_TIMEOUT_SECONDS)
        except Exception:
            pass

        self._connected = True

    def _with_reconnect(self, fn, *args, **kwargs):
        """
        Run an SFTP operation with one reconnect+retry on common connection failures/timeouts.
        """
        self.connect()
        try:
            return fn(*args, **kwargs)
        except (EOFError, socket.timeout, OSError, paramiko.SSHException):
            if not RETRY_ONCE:
                raise
            # One retry after reconnect
            self._connected = False
            self.close()
            self.connect()
            return fn(*args, **kwargs)

    def _ensure_remote_dir(self, remote_dir: str):
        """
        Create remote directories recursively. Uses reconnect wrapper so stat/mkdir won't hang indefinitely.
        """
        if not remote_dir:
            return

        remote_dir = remote_dir.replace("\\", "/")
        parts = remote_dir.strip("/").split("/")
        current = ""

        for part in parts:
            if not part:
                continue
            current += f"/{part}"

            def _stat():
                return self.sftp.stat(current)

            try:
                self._with_reconnect(_stat)
            except FileNotFoundError:

                def _mkdir():
                    return self.sftp.mkdir(current)

                self._with_reconnect(_mkdir)

    def _remote_exists(self, remote_path: str) -> bool:
        remote_path = remote_path.replace("\\", "/")

        def _stat():
            return self.sftp.stat(remote_path)

        try:
            self._with_reconnect(_stat)
            return True
        except FileNotFoundError:
            return False

    def _unique_remote_path(self, remote_path: str) -> str:
        """
        If remote_path already exists, append a timestamp suffix to avoid overwrite.
        Returns a non-existing remote path (best-effort).
        """
        remote_path = remote_path.replace("\\", "/")
        if not self._remote_exists(remote_path):
            return remote_path

        p = Path(remote_path)
        parent = str(p.parent).replace("\\", "/")
        stem = p.stem
        suffix = p.suffix

        # Try a few times (in case of rapid repeated uploads)
        for _ in range(6):
            ts = time.strftime("%Y%m%d_%H%M%S")
            candidate = f"{parent}/{stem}_{ts}{suffix}".replace("\\", "/")
            if not self._remote_exists(candidate):
                return candidate
            time.sleep(1)

        # Last resort: epoch seconds
        return f"{parent}/{stem}_{int(time.time())}{suffix}".replace("\\", "/")

    def upload_file(self, local_path: Path, mailbox_folder: str) -> str:
        """
        Upload file into: <base>/<mailbox_folder>/<filename> (or suffixed filename on collision)

        Returns a string suitable for logging in main.py:
          "<mailbox_folder>/<actual_remote_filename>"
        """
        if not self.enabled:
            # Important: main.py catches exceptions and will NOT mark processed/cleanup.
            raise RuntimeError("SFTP is disabled (SFTP_ENABLED=false)")

        local_path = Path(local_path)

        remote_dir = f"{SFTP_REMOTE_BASE_DIR}/{mailbox_folder}".replace("\\", "/")
        remote_path = f"{remote_dir}/{local_path.name}".replace("\\", "/")

        # Ensure folder exists (safe + retry)
        self._ensure_remote_dir(remote_dir)

        # Collision avoidance
        remote_path = self._unique_remote_path(remote_path)

        # Upload (safe + retry)
        def _put():
            return self.sftp.put(str(local_path), remote_path)

        self._with_reconnect(_put)

        # Return what we actually used, relative to base dir, so logs look clean.
        base = str(SFTP_REMOTE_BASE_DIR).replace("\\", "/").rstrip("/")
        rel = remote_path
        if rel.startswith(base + "/"):
            rel = rel[len(base) + 1 :]
        return rel

    def close(self):
        try:
            if self.sftp:
                try:
                    # Avoid hangs on close
                    self.sftp.close()
                except Exception:
                    pass
        finally:
            self.sftp = None

        try:
            if self.transport:
                try:
                    self.transport.close()
                except Exception:
                    pass
        finally:
            self.transport = None
            self._connected = False
