import unittest
import time
from PIL import Image, ImageDraw
from capture.watcher import compute_dhash, hamming_distance, ScreenWatcher
from capture.screen import ScreenCaptureData


class TestScreenWatcher(unittest.TestCase):

    def test_dhash_identical_images(self):
        # Create identical 100x100 images
        img1 = Image.new("RGB", (100, 100), color=(120, 120, 120))
        img2 = Image.new("RGB", (100, 100), color=(120, 120, 120))

        h1 = compute_dhash(img1)
        h2 = compute_dhash(img2)

        self.assertEqual(h1, h2)
        self.assertEqual(hamming_distance(h1, h2), 0)

    def test_dhash_different_images(self):
        # Create two distinct patterns
        img1 = Image.new("RGB", (100, 100), color=(0, 0, 0))
        draw1 = ImageDraw.Draw(img1)
        draw1.rectangle([0, 0, 50, 100], fill=(255, 255, 255))

        img2 = Image.new("RGB", (100, 100), color=(0, 0, 0))
        draw2 = ImageDraw.Draw(img2)
        draw2.rectangle([50, 0, 100, 100], fill=(255, 255, 255))

        h1 = compute_dhash(img1)
        h2 = compute_dhash(img2)

        dist = hamming_distance(h1, h2)
        self.assertGreater(dist, 4)

    def test_watcher_lifecycle_and_cache(self):
        changes_received = []

        def on_change(screen_data):
            changes_received.append(screen_data)

        watcher = ScreenWatcher(
            interval=0.5,
            change_threshold=4,
            on_change_callback=on_change
        )

        self.assertFalse(watcher.is_running)
        watcher.start()
        self.assertTrue(watcher.is_running)

        # Retrieve latest screen
        screen_data = watcher.get_latest_screen()
        self.assertIsNotNone(screen_data)
        self.assertIsInstance(screen_data, ScreenCaptureData)
        self.assertIsNotNone(screen_data.image_b64)
        self.assertIsNotNone(screen_data.bbox)

        # Stop cleanly
        watcher.stop(timeout=1.0)
        self.assertFalse(watcher.is_running)


if __name__ == "__main__":
    unittest.main()
