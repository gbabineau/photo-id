"""
Tests  photo_id/process_quiz.py
"""
import json
import unittest
from unittest import mock
import photo_id.get_taxonomy


class TestProcessQuiz(unittest.TestCase):

    def test_process_quiz_file(self):
        """ tests the function with that name """
        test_json = {
            "start_month": 5,
            "end_month": 6,
            "location": "",
            "species": [
                {"comName": "Common Chaffinch"},
                {"comName": "Brambling"},
                {"comName": "Eurasian Bullfinch"},
                {"comName": "Eurasian Bullfinch"},
                {"comName": "Eurasian Bullfrog"},
            ]}

        taxonomy = [
            {"comName": "Brambling", "taxonOrder": 1},
            {"comName": "Common Chaffinch", "taxonOrder": 2},
            {"comName": "Eurasian Bullfinch", "taxonOrder": 3},
            {"comName": "Ortolan Bunting", "taxonOrder": 4},
            {"comName": "Reed Bunting", "taxonOrder": 5}
        ]

        expected = {
            "location": "",
            "start_month": 5,
            "end_month": 6,
            "notes": "",
            "species": [
                {"comName": "Brambling", "taxonOrder": 1, "notes": ""},
                {"comName": "Common Chaffinch", "taxonOrder": 2, "notes": ""},
                {"comName": "Eurasian Bullfinch", "taxonOrder": 3, "notes": ""},
            ]
        }
        # Now Test
        with mock.patch('photo_id.process_quiz.logging.info') as mock_logging, \
                mock.patch("builtins.open", mock.mock_open(read_data=json.dumps(test_json))) as mock_file:
            result = photo_id.process_quiz.process_quiz_file(
                'quiz.json', taxonomy)
            mock_file.assert_called_with(
                "quiz.json", encoding='utf-8', mode='rt')
            self.assertEqual(expected, result)
