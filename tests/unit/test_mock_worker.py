import sys
import tempfile
import unittest
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / 'services' / 'tts_worker'))
from mock_worker import synthesize


class MockWorkerTests(unittest.TestCase):
    def test_creates_readable_wav(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'sample.wav'
            synthesize('Ein kurzer Test.', output)
            with wave.open(str(output)) as audio:
                self.assertEqual(audio.getnchannels(), 1)
                self.assertGreater(audio.getnframes(), 0)
