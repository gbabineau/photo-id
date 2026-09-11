import hashlib
import threading
import time
from pathlib import Path
from typing import Optional, Union


class URLCache:
    _instance = None
    _lock = threading.Lock()
    cache_dir = Path()
    max_age_seconds = 0

    def __new__(
        cls, cache_dir: Path = Path("./.cache/pages"), max_age_days: int = 180
    ):
        # Thread-safe Singleton initialization
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(URLCache, cls).__new__(cls)
                # Initialize state once
                cls._instance.cache_dir = Path(cache_dir)
                cls._instance.max_age_seconds = max_age_days * 86400
                cls._instance.cache_dir.mkdir(parents=True, exist_ok=True)
                cls._instance._cleanup_expired_files()
        return cls._instance

    def _cleanup_expired_files(self) -> None:
        """Deletes cached files older than max_age  during initialization."""
        if not self.cache_dir.exists():
            return

        now = time.time()
        for cache_path in self.cache_dir.glob("*.html"):
            try:
                file_age = now - cache_path.stat().st_mtime
                if file_age > self.max_age_seconds:
                    cache_path.unlink(missing_ok=True)
            except OSError:
                continue

    def _get_cache_path(self, url: str) -> Path:
        """Generates a unique, filesystem-safe filename using MD5 hash of the URL."""
        url_hash = hashlib.md5(  # NOSONAR hashing is safe
            url.encode("utf-8")
        ).hexdigest()
        return self.cache_dir / f"{url_hash}.html"

    def get(self, url: str) -> Optional[bytes]:
        """Returns cached bytes if present and less than max_age_days old, else None."""
        cache_path = self._get_cache_path(url)

        if not cache_path.exists():
            return None

        file_age = time.time() - cache_path.stat().st_mtime
        if file_age > self.max_age_seconds:
            print(
                f"[Cache] Expired ({int(file_age // 86400)} days old). Fetching fresh..."
            )
            cache_path.unlink(missing_ok=True)
            return None

        return cache_path.read_bytes()

    def set(self, url: str, content: Union[str, bytes, bytearray]) -> None:
        """Saves content bytes to the cache directory. Accepts text as UTF-8 bytes too."""
        cache_path = self._get_cache_path(url)

        if isinstance(content, str):
            content = content.encode("utf-8")
        elif isinstance(content, bytearray):
            content = bytes(content)

        cache_path.write_bytes(content)
