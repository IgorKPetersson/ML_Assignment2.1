"""Unit tests for gui/server.py utilities. Run: python gui/test_server.py"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import server


class TestParseDotenv(unittest.TestCase):
    def test_reads_key_value_pairs(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write('MODEL=gpt-4.1-mini\nMAX_STEPS=10\n')
            path = f.name
        result = server.parse_dotenv(path)
        self.assertEqual(result['MODEL'], 'gpt-4.1-mini')
        self.assertEqual(result['MAX_STEPS'], '10')

    def test_skips_comments_and_blanks(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write('# comment\n\nKEY=val\n')
            path = f.name
        result = server.parse_dotenv(path)
        self.assertNotIn('# comment', result)
        self.assertEqual(result['KEY'], 'val')

    def test_returns_empty_dict_if_file_missing(self):
        result = server.parse_dotenv('/nonexistent/.env')
        self.assertEqual(result, {})

    def test_strips_quotes(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write('KEY="quoted value"\n')
            path = f.name
        result = server.parse_dotenv(path)
        self.assertEqual(result['KEY'], 'quoted value')


class TestMaskSecret(unittest.TestCase):
    def test_masks_openai_key(self):
        result = server.mask_secret('sk-proj-abc123xyz456')
        self.assertTrue(result.startswith('sk-pro'))
        self.assertIn('•', result)
        self.assertNotIn('abc123xyz456', result)

    def test_leaves_non_secret_unchanged(self):
        self.assertEqual(server.mask_secret('gpt-4.1-mini'), 'gpt-4.1-mini')
        self.assertEqual(server.mask_secret('10'), '10')


class TestLogManager(unittest.TestCase):
    def test_load_returns_empty_list_if_missing(self):
        result = server.load_logs('/nonexistent/logs.json')
        self.assertEqual(result, [])

    def test_append_and_load(self):
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            path = f.name
        server.append_log(path, {'task': 'test', 'output': 'ok'})
        logs = server.load_logs(path)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]['task'], 'test')

    def test_capped_at_50(self):
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            path = f.name
        for i in range(55):
            server.append_log(path, {'task': str(i)})
        logs = server.load_logs(path)
        self.assertEqual(len(logs), 50)
        self.assertEqual(logs[-1]['task'], '54')


if __name__ == '__main__':
    unittest.main(verbosity=2)
