from pathlib import Path
import paramiko
from config import (
    SFTP_ENABLED,
    SFTP_HOST,
    SFTP_PORT,
    SFTP_USERNAME,
    SFTP_PRIVATE_KEY_PATH,
    SFTP_REMOTE_BASE_DIR,
)


class SFTPClient:
    def __init__(self):
        self.enabled = SFTP_ENABLED
        self.transport = None
        self.sftp = None

    def connect(self):
        if not self.enabled:
            return

        key_path = Path(SFTP_PRIVATE_KEY_PATH)

        if not key_path.exists():
            raise FileNotFoundError(f"SFTP private key not found: {key_path}")

        if not key_path.is_file():
            raise ValueError(f"SFTP private key path is not a file: {key_path}")

        key = None
        last_error = None

        # Correct Paramiko key auto-detection
        for key_cls in (
            paramiko.Ed25519Key,
            paramiko.RSAKey,
            paramiko.ECDSAKey,
        ):
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

        self.transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
        self.transport.connect(
            username=SFTP_USERNAME,
            pkey=key,
        )

        self.sftp = paramiko.SFTPClient.from_transport(self.transport)

    def upload_file(self, local_path: Path, mailbox_folder: str):
        if not self.enabled:
            return

        remote_dir = f"{SFTP_REMOTE_BASE_DIR}/{mailbox_folder}"
        remote_path = f"{remote_dir}/{local_path.name}"

        self._ensure_remote_dir(remote_dir)
        self.sftp.put(str(local_path), remote_path)

    def _ensure_remote_dir(self, remote_dir: str):
        parts = remote_dir.strip("/").split("/")
        current = ""

        for part in parts:
            current += f"/{part}"
            try:
                self.sftp.stat(current)
            except FileNotFoundError:
                self.sftp.mkdir(current)

    def close(self):
        if self.sftp:
            self.sftp.close()
        if self.transport:
            self.transport.close()
