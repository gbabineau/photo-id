import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from photo_id.url_cache import URLCache


class TestURLCache(unittest.TestCase):
    def setUp(self):
        URLCache._instance = None
        self.temp_directory = tempfile.TemporaryDirectory()
        self.cache_directory = Path(self.temp_directory.name) / "pages"
        self.cache = URLCache(self.cache_directory, max_age_days=30)

    def tearDown(self):
        URLCache._instance = None
        self.temp_directory.cleanup()

    def test_initialization_creates_cache_directory(self):
        self.assertTrue(self.cache_directory.is_dir())
        self.assertEqual(self.cache.cache_dir, self.cache_directory)
        self.assertEqual(self.cache.max_age_seconds, 30 * 86400)

    def test_initialization_returns_singleton(self):
        second_cache = URLCache(Path("ignored"), max_age_days=1)

        self.assertIs(second_cache, self.cache)
        self.assertEqual(second_cache.cache_dir, self.cache_directory)
        self.assertEqual(second_cache.max_age_seconds, 30 * 86400)

    def test_get_returns_none_when_url_is_not_cached(self):
        self.assertIsNone(self.cache.get("https://example.test/page"))

    def test_set_and_get_round_trip_utf8_text(self):
        url = "https://example.test/page"
        self.cache.set(url, "Hello, birds")

        self.assertEqual(self.cache.get(url), b"Hello, birds")

    def test_set_and_get_round_trip_bytes(self):
        url = "https://example.test/image"
        content = b"\x00\x01\xff"
        self.cache.set(url, content)

        self.assertEqual(self.cache.get(url), content)

    def test_set_converts_bytearray_to_bytes(self):
        url = "https://example.test/page"
        self.cache.set(url, bytearray(b"content"))

        self.assertEqual(self.cache.get(url), b"content")

    def test_different_urls_use_different_cache_files(self):
        first_path = self.cache._get_cache_path("https://example.test/one")
        second_path = self.cache._get_cache_path("https://example.test/two")

        self.assertNotEqual(first_path, second_path)
        self.assertEqual(first_path.parent, self.cache_directory)
        self.assertTrue(first_path.name.endswith(".html"))

    def test_expired_cache_entry_is_deleted_and_returns_none(self):
        url = "https://example.test/expired"
        self.cache.set(url, "old content")
        cache_path = self.cache._get_cache_path(url)
        expired_time = time.time() - self.cache.max_age_seconds - 86400
        os.utime(cache_path, (expired_time, expired_time))

        with mock.patch("builtins.print") as mock_print:
            result = self.cache.get(url)

        self.assertIsNone(result)
        self.assertFalse(cache_path.exists())
        mock_print.assert_called_once()
        self.assertIn("Expired", mock_print.call_args.args[0])

    def test_cleanup_removes_expired_html_and_preserves_other_files(self):
        expired_path = self.cache_directory / "expired.html"
        current_path = self.cache_directory / "current.html"
        other_path = self.cache_directory / "notes.txt"
        expired_path.write_text("old", encoding="utf-8")
        current_path.write_text("current", encoding="utf-8")
        other_path.write_text("keep", encoding="utf-8")
        expired_time = time.time() - self.cache.max_age_seconds - 1
        os.utime(expired_path, (expired_time, expired_time))

        self.cache._cleanup_expired_files()

        self.assertFalse(expired_path.exists())
        self.assertTrue(current_path.exists())
        self.assertTrue(other_path.exists())

    def test_cleanup_returns_when_cache_directory_is_missing(self):
        cache = object.__new__(URLCache)
        cache.cache_dir = self.cache_directory / "missing"

        cache._cleanup_expired_files()

    @mock.patch("photo_id.url_cache.time.time", return_value=1000)
    def test_cleanup_ignores_os_errors_for_cache_files(self, _mock_time):
        expired_path = mock.Mock()
        expired_path.stat.return_value.st_mtime = 0
        expired_path.unlink.side_effect = OSError("cannot remove")
        inaccessible_path = mock.Mock()
        inaccessible_path.stat.side_effect = OSError("cannot inspect")
        self.cache.cache_dir = mock.Mock()
        self.cache.cache_dir.exists.return_value = True
        self.cache.cache_dir.glob.return_value = [
            expired_path,
            inaccessible_path,
        ]
        self.cache.max_age_seconds = 1

        self.cache._cleanup_expired_files()

        expired_path.unlink.assert_called_once_with(missing_ok=True)
        inaccessible_path.unlink.assert_not_called()


if __name__ == "__main__":
    unittest.main()
