from __future__ import annotations

import base64
import hashlib
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import unquote, urlparse

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import BackupArtifact, TelegramOutbox


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def enqueue_outbox(db: Session, *, idempotency_key: str, event_type: str, payload: dict) -> TelegramOutbox:
    existing = db.query(TelegramOutbox).filter_by(idempotency_key=idempotency_key).first()
    if existing:
        return existing
    row = TelegramOutbox(idempotency_key=idempotency_key, event_type=event_type, payload=payload)
    try:
        with db.begin_nested():
            db.add(row)
            db.flush()
    except IntegrityError:
        return db.query(TelegramOutbox).filter_by(idempotency_key=idempotency_key).one()
    return row


def dispatch_outbox(db: Session, sender: Callable[[TelegramOutbox], None], *, limit: int = 25, max_attempts: int = 6) -> int:
    rows = (db.query(TelegramOutbox)
            .filter(TelegramOutbox.status.in_(("PENDING", "RETRYING")), TelegramOutbox.next_attempt_at <= now())
            .order_by(TelegramOutbox.next_attempt_at, TelegramOutbox.id)
            .limit(limit).with_for_update(skip_locked=True).all())
    processed = 0
    for row in rows:
        try:
            sender(row)
            row.status = "DELIVERED"
            row.completed_at = now()
            row.last_error_code = None
            if row.event_type == "backup.ready" and row.payload.get("artifact_id"):
                artifact = db.get(BackupArtifact, row.payload["artifact_id"])
                if artifact:
                    artifact.delivery_status = "DELIVERED"
                    artifact.delivered_at = now()
                    artifact.error_code = None
        except Exception as exc:
            row.attempts += 1
            row.last_error_code = type(exc).__name__[:64]
            row.status = "DEAD_LETTER" if row.attempts >= max_attempts else "RETRYING"
            row.completed_at = now() if row.status == "DEAD_LETTER" else None
            row.next_attempt_at = now() + timedelta(seconds=min(3600, 30 * (2 ** min(row.attempts, 7))))
            if row.event_type == "backup.ready" and row.payload.get("artifact_id"):
                artifact = db.get(BackupArtifact, row.payload["artifact_id"])
                if artifact:
                    artifact.delivery_status = "FAILED" if row.status == "DEAD_LETTER" else "RETRYING"
                    artifact.error_code = row.last_error_code
        processed += 1
    db.commit()
    return processed


def purge_outbox(db: Session, *, batch_size: int = 500, current: datetime | None = None) -> int:
    current = current or now()
    ids = [r[0] for r in (db.query(TelegramOutbox.id)
        .filter(((TelegramOutbox.status == "DELIVERED") & (TelegramOutbox.completed_at < current - timedelta(days=30))) |
                ((TelegramOutbox.status.in_(("FAILED", "DEAD_LETTER"))) & (TelegramOutbox.completed_at < current - timedelta(days=90))))
        .order_by(TelegramOutbox.id).limit(batch_size).all())]
    if ids:
        db.query(TelegramOutbox).filter(TelegramOutbox.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
    return len(ids)


def purge_delivered_backup_files(db: Session, *, current: datetime | None = None, batch_size: int = 100) -> int:
    current = current or now()
    newest_valid_id = (db.query(BackupArtifact.id)
        .filter(BackupArtifact.generation_status == "SUCCESS")
        .order_by(BackupArtifact.created_at.desc(), BackupArtifact.id.desc()).limit(1).scalar())
    rows = (db.query(BackupArtifact)
        .filter(BackupArtifact.delivery_status == "DELIVERED",
                BackupArtifact.delivered_at < current - timedelta(hours=48),
                BackupArtifact.id != newest_valid_id)
        .order_by(BackupArtifact.id).limit(batch_size).all())
    removed = 0
    for row in rows:
        if row.encrypted_path:
            Path(row.encrypted_path).unlink(missing_ok=True)
            row.encrypted_path = None
            removed += 1
    db.commit()
    return removed


def encrypt_backup(source: Path, destination: Path, key_b64: str) -> tuple[int, str]:
    key = base64.b64decode(key_b64, validate=True)
    if len(key) != 32:
        raise ValueError("STAGE11_BACKUP_KEY must decode to exactly 32 bytes")
    plaintext = source.read_bytes()
    if not plaintext or b"CREATE TABLE" not in plaintext.upper():
        raise ValueError("backup_artifact_invalid")
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, b"marzban-mysql-backup-v1")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(b"MZB1" + nonce + ciphertext)
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    return destination.stat().st_size, digest


def decrypt_backup(source: Path, destination: Path, key_b64: str) -> None:
    raw = source.read_bytes()
    if raw[:4] != b"MZB1":
        raise ValueError("backup_envelope_invalid")
    key = base64.b64decode(key_b64, validate=True)
    destination.write_bytes(AESGCM(key).decrypt(raw[4:16], raw[16:], b"marzban-mysql-backup-v1"))


def mysql_dump_command(database_url: str) -> tuple[list[str], dict[str, str], str]:
    parsed = urlparse(database_url.replace("mysql+pymysql://", "mysql://", 1))
    database = parsed.path.lstrip("/")
    command = ["mysqldump", "--single-transaction", "--routines", "--triggers", "--hex-blob",
               "--host", parsed.hostname or "127.0.0.1", "--port", str(parsed.port or 3306),
               "--user", unquote(parsed.username or "root"), database]
    env = os.environ.copy()
    if parsed.password:
        env["MYSQL_PWD"] = unquote(parsed.password)
    return command, env, database


def generate_backup(database_url: str, spool: Path, key_b64: str, period_key: str) -> tuple[Path, int, str, str]:
    command, env, database = mysql_dump_command(database_url)
    plain = spool / f"{period_key}.sql.tmp"
    encrypted = spool / f"{period_key}.sql.aesgcm"
    spool.mkdir(parents=True, exist_ok=True)
    with plain.open("wb") as output:
        result = subprocess.run(command, stdout=output, stderr=subprocess.PIPE, env=env, check=False)
    try:
        if result.returncode != 0:
            raise RuntimeError("mysqldump_failed")
        size, digest = encrypt_backup(plain, encrypted, key_b64)
        return encrypted, size, digest, database
    finally:
        plain.unlink(missing_ok=True)
