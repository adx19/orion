"""
Tests for agent.response_parser.parse.

Run from the project root:
    python -m unittest discover tests
"""

import unittest

from agent.response_parser import InvalidResponseError, parse


class ParseFencedJsonTests(unittest.TestCase):
    def test_json_fence(self):
        raw = '```json\n{"thought": "go", "action": "click", "target": "Sign in"}\n```'
        self.assertEqual(
            parse(raw),
            {"thought": "go", "action": "click", "target": "Sign in"},
        )

    def test_plain_fence_with_surrounding_prose(self):
        raw = 'Here is my answer:\n```\n{"action": "press_enter"}\n```\nThanks!'
        self.assertEqual(parse(raw), {"action": "press_enter"})

    def test_unfenced_json(self):
        self.assertEqual(
            parse('  {"action": "scroll", "direction": "down"}  '),
            {"action": "scroll", "direction": "down"},
        )


class ParseMissingActionTests(unittest.TestCase):
    def test_missing_action_key(self):
        with self.assertRaisesRegex(InvalidResponseError, "missing 'action'"):
            parse('{"thought": "I am not sure", "target": "Login"}')

    def test_missing_action_inside_fence(self):
        with self.assertRaises(InvalidResponseError):
            parse('```json\n{"thought": "hmm"}\n```')

    def test_unknown_action(self):
        with self.assertRaisesRegex(InvalidResponseError, "Unknown action"):
            parse('{"action": "teleport"}')


class ParseEmptyTargetTests(unittest.TestCase):
    def test_click_empty_target_rejected(self):
        with self.assertRaises(InvalidResponseError):
            parse('{"action": "click", "target": ""}')

    def test_click_whitespace_target_rejected(self):
        with self.assertRaises(InvalidResponseError):
            parse('{"action": "click", "target": "   "}')

    def test_click_empty_target_with_partial_coordinates_rejected(self):
        with self.assertRaises(InvalidResponseError):
            parse('{"action": "click", "target": "", "x": 100}')

    def test_click_non_numeric_coordinates_rejected(self):
        with self.assertRaises(InvalidResponseError):
            parse('{"action": "click", "x": "100", "y": "200"}')

    def test_click_empty_target_with_coordinates_accepted(self):
        action = parse('{"action": "click", "target": "", "x": 100, "y": 200}')
        self.assertEqual((action["x"], action["y"]), (100, 200))

    def test_click_non_empty_target_accepted(self):
        self.assertEqual(parse('{"action": "click", "target": "Submit"}')["target"], "Submit")


if __name__ == "__main__":
    unittest.main()
