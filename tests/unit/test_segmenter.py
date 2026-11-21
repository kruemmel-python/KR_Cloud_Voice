import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / 'services' / 'segmenter'))
from segmenter import segment_text


class SegmenterTests(unittest.TestCase):
    def test_does_not_cross_markdown_chapters(self):
        parts = segment_text('# Eins\n' + 'Ein Satz. ' * 40 + '\n# Zwei\n' + 'Noch ein Satz. ' * 40)
        self.assertGreater(len(parts), 1)
        self.assertEqual({chapter for chapter, _ in parts}, {1, 2})

    def test_omits_empty_input(self):
        self.assertEqual(segment_text('   '), [])
