import unittest
from unittest.mock import mock_open, patch
from photo_id.get_have_list import get_have_list


class TestGetHaveList(unittest.TestCase):
    def test_get_have_list_valid_csv(self):
        mock_data = "Row #,Taxon Order,Category,Common Name,Scientific Name,Count\n1,100,Bird,Common Bird,Scientific Bird,1"
        with patch("builtins.open", mock_open(read_data=mock_data)):
            result = get_have_list("valid.csv")
            self.assertEqual(
                result, [{"comName": "Common Bird", "taxonOrder": 100}]
            )

    def test_get_have_list_invalid_header(self):
        mock_data = "Incorrect header"
        with patch("builtins.open", mock_open(read_data=mock_data)), patch(
            "logging.error"
        ) as mocked_log:
            get_have_list("invalid_header.csv")
            mocked_log.assert_called_once()

    def test_get_have_list_non_existent_file(self):
        with patch("builtins.open", side_effect=FileNotFoundError):
            with self.assertRaises(FileNotFoundError):
                get_have_list("non_existent.csv")

    def test_get_have_list_empty_file(self):
        with patch("builtins.open", mock_open(read_data="")):
            result = get_have_list("empty.csv")
            self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
