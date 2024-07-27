"""
Tests  photo_id/process_quiz.py
"""
import json
import os
import unittest
from unittest import TestCase, mock

import photo_id.get_taxonomy
import photo_id.process_quiz
from photo_id.process_quiz import build_quiz_from_target_species, sort_quiz


class TestSortedSpecies(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures, if any."""
        self.taxonomy = [
            {"comName": "Brambling", "taxonOrder": 1},
            {"comName": "Common Chaffinch", "taxonOrder": 2},
            {"comName": "Eurasian Bullfinch", "taxonOrder": 3},
            {"comName": "Ortolan Bunting", "taxonOrder": 4},
            {"comName": "Reed Bunting", "taxonOrder": 5}
        ]

    def test_sorted_species_correct_order(self):
        """Test if species are sorted correctly by their taxonomic order."""
        initial_list = [
            {"comName": "Eurasian Bullfinch"},
            {"comName": "Brambling"},
            {"comName": "Common Chaffinch"}
        ]
        expected = [
            {"comName": "Brambling", "taxonOrder": 1, "notes": ""},
            {"comName": "Common Chaffinch", "taxonOrder": 2, "notes": ""},
            {"comName": "Eurasian Bullfinch", "taxonOrder": 3, "notes": ""}
        ]
        result = photo_id.process_quiz.sorted_species(
            initial_list, self.taxonomy)
        self.assertEqual(expected, result)

    def test_sorted_species_with_duplicates(self):
        """Test if duplicate species are removed."""
        initial_list = [
            {"comName": "Eurasian Bullfinch"},
            {"comName": "Brambling"},
            {"comName": "Eurasian Bullfinch"}
        ]
        expected = [
            {"comName": "Brambling", "taxonOrder": 1, "notes": ""},
            {"comName": "Eurasian Bullfinch", "taxonOrder": 3, "notes": ""}
        ]
        result = photo_id.process_quiz.sorted_species(
            initial_list, self.taxonomy)
        self.assertEqual(expected, result)

    def test_sorted_species_with_unfound_species(self):
        """Test if species not found in taxonomy are ignored."""
        initial_list = [
            {"comName": "Eurasian Bullfinch"},
            {"comName": "Brambling"},
            {"comName": "Unknown Species"}
        ]
        expected = [
            {"comName": "Brambling", "taxonOrder": 1, "notes": ""},
            {"comName": "Eurasian Bullfinch", "taxonOrder": 3, "notes": ""}
        ]
        result = photo_id.process_quiz.sorted_species(
            initial_list, self.taxonomy)
        self.assertEqual(expected, result)

    def test_sorted_species_with_additional_info(self):
        """Test if additional information (like 'notes') is preserved."""
        initial_list = [
            {"comName": "Eurasian Bullfinch", "notes": "Noisy"},
            {"comName": "Brambling", "notes": "None"}
        ]
        expected = [
            {"comName": "Brambling", "taxonOrder": 1, "notes": "None"},
            {"comName": "Eurasian Bullfinch",
                "taxonOrder": 3, "notes": "Noisy"}
        ]
        result = photo_id.process_quiz.sorted_species(
            initial_list, self.taxonomy)
        self.assertEqual(expected, result)

    def test_sorted_species_empty_list(self):
        """Test if an empty list is handled correctly."""
        initial_list = []
        expected = []
        result = photo_id.process_quiz.sorted_species(
            initial_list, self.taxonomy)
        self.assertEqual(expected, result)


class TestProcessQuizFile(unittest.TestCase):

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
            self.assertEqual(mock_logging.call_count, 2)

class TestSortQuiz(unittest.TestCase):
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('json.load')
    @mock.patch('os.path.exists')
    def test_sort_quiz_correct_order(self, mock_exists, mock_json_load, mock_open):
        # Setup mock behavior
        mock_exists.return_value = True
        mock_json_load.return_value = {
            'species': [
                {'comName': 'Brambling'},
                {'comName': 'Common Chaffinch'},
                {'comName': 'Eurasian Bullfinch'}
            ],
            'location': 'Test Location',
            'start_month': 1,
            'end_month': 12
        }

        # Define the expected taxonomy order
        taxonomy = [
            {"comName": "Brambling", "taxonOrder": 1},
            {"comName": "Common Chaffinch", "taxonOrder": 2},
            {"comName": "Eurasian Bullfinch", "taxonOrder": 3}
        ]

        # Call the function under test
        sort_quiz('dummy_file_name.json', taxonomy)

        # Assertions to verify the file operations and the sorted order
        mock_open.assert_called_with(
            'dummy_file_name.json.sorted', encoding='utf-8', mode='wt')


class TestBuildQuizFromTargetSpecies(TestCase):

    @mock.patch('builtins.open', new_callable=mock.mock_open, read_data='1.\nSpecies A\n10.\n2.\nSpecies B\n5.\n')
    @mock.patch('json.dump')
    @mock.patch('os.path.exists', return_value=True)
    def test_with_valid_input(self, _mock_exists, _mock_json_dump, mock_open):
        build_quiz_from_target_species(
            'input.txt', 3, 'output.json', 5, 6, 'LC')
        mock_open.assert_called_with('output.json', 'wt', encoding='utf-8')
        expected_result = {
            "start_month": 5,
            "end_month": 6,
            "location": "LC",
            "species": [
                {"comName": "Species A", "frequency": 10, "notes": ""},
                {"comName": "Species B", "frequency": 5, "notes": ""}
            ]
        }
        mock_open().write.assert_called_with(json.dumps(expected_result, indent=2))

    @mock.patch('builtins.open', new_callable=mock.mock_open, read_data='')
    @mock.patch('json.dump')
    @mock.patch('os.path.exists', return_value=True)
    def test_with_empty_input_file(self, _mock_exists, _mock_json_dump, mock_open):
        build_quiz_from_target_species(
            'input.txt', 3, 'output.json', 5, 6, 'LC')
        expected_result = {
            "start_month": 5,
            "end_month": 6,
            "location": "LC",
            "species": []
        }
        mock_open().write.assert_called_with(json.dumps(expected_result, indent=2))

    @mock.patch('builtins.open', side_effect=FileNotFoundError)
    def test_with_non_existing_input_file(self, _mock_open):
        with self.assertRaises(FileNotFoundError):
            build_quiz_from_target_species(
                'non_existing.txt', 3, 'output.json', 5, 6, 'LC')


class TestSplitQuiz(unittest.TestCase):
    @mock.patch('json.dump')
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('photo_id.process_quiz.process_quiz_file')
    @mock.patch('photo_id.process_quiz.sorted_species')
    def test_split_quiz_single_file(self, mock_sorted_species, mock_process_quiz_file, mock_open, mock_json_dump):
        """
        Test if split_quiz correctly handles a case where the quiz does not need to be split (i.e., fits in a single file).
        """
        # Setup
        taxonomy = [{"comName": "Species A", "taxonOrder": 1}]
        quiz_data = {
            "location": "Test Location",
            "start_month": 1,
            "end_month": 12,
            "species": [{"comName": "Species A"}]
        }
        mock_process_quiz_file.return_value = quiz_data
        mock_sorted_species.return_value = quiz_data['species']

        # Execute
        photo_id.process_quiz.split_quiz("input_file.json", 10, taxonomy)

        # Assert
        mock_process_quiz_file.assert_called_once_with(
            name="input_file.json", taxonomy=taxonomy)
        self.assertEqual(mock_open.mock_calls[0][1][0].lower(
        ), f"{os.getcwd()}/input_file_Part1.json".lower())
        mock_open.assert_called_with(
            mock.ANY, "wt", encoding='utf-8')
        mock_json_dump.assert_called_with(quiz_data, mock.ANY, indent=2)

    @mock.patch('json.dump')
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('photo_id.process_quiz.process_quiz_file')
    @mock.patch('photo_id.process_quiz.sorted_species')
    def test_split_quiz_multiple_files(self, mock_sorted_species, mock_process_quiz_file, mock_open, mock_json_dump):
        """
        Test if split_quiz correctly splits the quiz into multiple files when the number of species exceeds max_size.
        """
        # Setup
        taxonomy = [{"comName": "Species A", "taxonOrder": 1},
                    {"comName": "Species B", "taxonOrder": 2}]
        quiz_data = {
            "location": "Test Location",
            "start_month": 1,
            "end_month": 12,
            "species": [{"comName": "Species A"}, {"comName": "Species B"}]
        }
        mock_process_quiz_file.return_value = quiz_data
        mock_sorted_species.return_value = quiz_data['species']

        # Execute
        photo_id.process_quiz.split_quiz("input_file.json", 1, taxonomy)

        # Assert
        mock_process_quiz_file.assert_called_once_with(
            name="input_file.json", taxonomy=taxonomy)
        self.assertEqual(mock_open.call_count, 2)
        self.assertEqual(mock_json_dump.call_count, 2)

    @mock.patch('json.dump')
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('photo_id.process_quiz.process_quiz_file')
    @mock.patch('photo_id.process_quiz.sorted_species')
    def test_split_quiz_empty_species_list(self, mock_sorted_species, mock_process_quiz_file, mock_open, _mock_json_dump):
        """
        Test if split_quiz correctly handles an empty species list.
        """
        # Setup
        taxonomy = []
        quiz_data = {
            "location": "Test Location",
            "start_month": 1,
            "end_month": 12,
            "species": []
        }
        mock_process_quiz_file.return_value = quiz_data
        mock_sorted_species.return_value = quiz_data['species']

        # Execute
        photo_id.process_quiz.split_quiz("input_file.json", 10, taxonomy)

        # Assert
        mock_process_quiz_file.assert_called_once_with(
            name="input_file.json", taxonomy=taxonomy)
        mock_open.assert_not_called()

    @mock.patch('json.dump')
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('photo_id.process_quiz.process_quiz_file')
    @mock.patch('photo_id.process_quiz.sorted_species')
    def test_split_quiz_file_naming(self, mock_sorted_species, mock_process_quiz_file, mock_open, _mock_json_dump):
        """
        Test if split_quiz generates correct file names for split files.
        """
        # Setup
        taxonomy = [{"comName": "Species A", "taxonOrder": 1}, {
            "comName": "Species B", "taxonOrder": 2}, {"comName": "Species C", "taxonOrder": 3}]
        quiz_data = {
            "location": "Test Location",
            "start_month": 1,
            "end_month": 12,
            "species": [{"comName": "Species A"}, {"comName": "Species B"}, {"comName": "Species C"}]
        }
        mock_process_quiz_file.return_value = quiz_data
        mock_sorted_species.return_value = quiz_data['species']

        # Execute
        photo_id.process_quiz.split_quiz("input_file.json", 1, taxonomy)

        # Assert
        self.assertEqual(mock_open.mock_calls[0][1][0].lower(
        ), f"{os.getcwd()}/input_file_Part1.json".lower())
        self.assertEqual(mock_open.mock_calls[3][1][0].lower(
        ), f"{os.getcwd()}/input_file_Part2.json".lower())
        self.assertEqual(mock_open.mock_calls[6][1][0].lower(
        ), f"{os.getcwd()}/input_file_Part3.json".lower())
