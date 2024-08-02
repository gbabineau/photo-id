import json
import requests
import unittest
import zipfile
from unittest import mock
from unittest.mock import MagicMock
from photo_id.get_size_data import (
    read_xlsx_to_dict,
    download_file,
    extract_file_from_zip,
    write_dict_to_json,
    read_dict_from_json,
    get_new_avonet_data,
    process_avonet_data,
    read_cached_avonet_data,
)


class TestReadXlsxToDict(unittest.TestCase):

    @mock.patch("photo_id.get_size_data.openpyxl.load_workbook")
    def test_successful_read(self, mock_load_workbook):
        # Mock workbook and sheet
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_load_workbook.return_value = mock_workbook
        mock_workbook.__getitem__.return_value = mock_sheet

        # Mock sheet rows
        mock_sheet.iter_rows.return_value = [
                ["Species2", "Wing.Length", "Habitat", "Mass"],
                ["SpeciesA", 10.5, "Forest", 1.2],
                ["SpeciesB", 12.3, "Desert", 1.5],
            ]

        expected_result = {
            "SpeciesA": {"Wing.Length": 10.5, "Habitat": "Forest", "Mass": 1.2},
            "SpeciesB": {"Wing.Length": 12.3, "Habitat": "Desert", "Mass": 1.5},
        }

        result = read_xlsx_to_dict(
            "dummy_path", "dummy_sheet", ["Species2", "Wing.Length", "Habitat", "Mass"]
        )
        self.assertEqual(result, expected_result)

    @mock.patch(
        "photo_id.get_size_data.openpyxl.load_workbook", side_effect=FileNotFoundError
    )
    @mock.patch("photo_id.get_size_data.logging.error")
    def test_file_not_found(self, mock_log_error, mock_load_workbook):
        with self.assertRaises(SystemExit):
            read_xlsx_to_dict(
                "dummy_path", "dummy_sheet", ["Species2", "Wing.Length", "Habitat", "Mass"]
            )
        mock_log_error.assert_called_with("The file '%s' was not found.", "dummy_path")

    @mock.patch("photo_id.get_size_data.openpyxl.load_workbook")
    @mock.patch("photo_id.get_size_data.logging.error")
    def test_sheet_not_found(self, mock_log_error, mock_load_workbook):
        mock_workbook = MagicMock()
        mock_load_workbook.return_value = mock_workbook
        mock_workbook.__getitem__.side_effect = KeyError
        with self.assertRaises(SystemExit):
            read_xlsx_to_dict(
                "dummy_path", "dummy_sheet", ["Species2", "Wing.Length", "Habitat", "Mass"]
            )
        mock_log_error.assert_called_with(
            "Error: The sheet '%s' does not exist in the workbook.", "dummy_sheet"
        )

    @mock.patch("photo_id.get_size_data.openpyxl.load_workbook")
    @mock.patch("photo_id.get_size_data.logging.error")
    def test_missing_columns(self, mock_log_error, mock_load_workbook):
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_load_workbook.return_value = mock_workbook
        mock_workbook.__getitem__.return_value = mock_sheet

        mock_sheet.iter_rows.return_value = [
            ["Species2", "Wing.Length",  "Mass"],
            ["SpeciesA", 10.5,  1.2],
            ["SpeciesB", 12.3,  1.5],
        ]

        with self.assertRaises(SystemExit):
            read_xlsx_to_dict("dummy_path", "dummy_sheet", ["Species2", "Habitat", "Mass"])
        mock_log_error.assert_called_with(
            "Some columns were not found in the sheet. Columns found: %s, Columns expected: %s",
            ["Species2", "Mass"],
            ["Species2", "Habitat", "Mass"],
        )

    @mock.patch("photo_id.get_size_data.openpyxl.load_workbook")
    @mock.patch("photo_id.get_size_data.logging.error")
    def test_insufficient_columns(self, mock_log_error, mock_load_workbook):
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_load_workbook.return_value = mock_workbook
        mock_workbook.__getitem__.return_value = mock_sheet

        mock_sheet.iter_rows.return_value = [
            ["Species2"],
            ["SpeciesA"],
            ["SpeciesB"],
        ]

        with self.assertRaises(SystemExit):
            read_xlsx_to_dict("dummy_path", "dummy_sheet", ["Species2"])

        mock_log_error.assert_called_with("There must be at least 2 columns to read.")


class TestDownloadFile(unittest.TestCase):

    @mock.patch("photo_id.get_size_data.requests.get")
    def test_successful_download(self, mock_get):
        # Mock the response object
        mock_response = MagicMock()
        mock_response.content = b"file content"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        with mock.patch("builtins.open", mock.mock_open()) as mock_file:
            download_file("http://example.com/file.zip", "dummy_path")
            mock_file.assert_called_once_with("dummy_path", "wb")
            mock_file().write.assert_called_once_with(b"file content")

    @mock.patch(
        "photo_id.get_size_data.requests.get", side_effect=requests.exceptions.HTTPError
    )
    @mock.patch("photo_id.get_size_data.logging.error")
    def test_http_error(self, mock_log_error, mock_get):
        with self.assertRaises(SystemExit):
            download_file("http://example.com/file.zip", "dummy_path")
        mock_log_error.assert_called_with(
            "Failed to download the file from %s. Reason: %s",
            "http://example.com/file.zip",
            mock.ANY,
        )

    @mock.patch(
        "photo_id.get_size_data.requests.get", side_effect=requests.exceptions.Timeout
    )
    @mock.patch("photo_id.get_size_data.logging.error")
    def test_timeout_error(self, mock_log_error, mock_get):
        with self.assertRaises(SystemExit):
            download_file("http://example.com/file.zip", "dummy_path")
        mock_log_error.assert_called_with(
            "Failed to download the file from %s. Reason: %s",
            "http://example.com/file.zip",
            mock.ANY,
        )

    @mock.patch("photo_id.get_size_data.requests.get")
    @mock.patch("photo_id.get_size_data.logging.error")
    def test_io_error(self, mock_log_error, mock_get):
        # Mock the response object
        mock_response = MagicMock()
        mock_response.content = b"file content"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        with mock.patch("builtins.open", mock.mock_open()) as mock_file:
            mock_file.side_effect = IOError
            with self.assertRaises(SystemExit):
                download_file("http://example.com/file.zip", "dummy_path")
            mock_log_error.assert_called_with(
                "Error: Failed to write the file to %s. Reason: %s",
                "dummy_path",
                mock.ANY,
            )


class TestExtractFileFromZip(unittest.TestCase):

    @mock.patch("photo_id.get_size_data.os.makedirs")
    @mock.patch("photo_id.get_size_data.zipfile.ZipFile")
    def test_successful_extraction(self, mock_zipfile, mock_makedirs):
        mock_zip = mock_zipfile.return_value.__enter__.return_value
        extract_file_from_zip("dummy_zip_path", "dummy_file_name", "dummy_dest_dir")
        mock_makedirs.assert_called_once_with("dummy_dest_dir", exist_ok=True)
        mock_zip.extract.assert_called_once_with("dummy_file_name", "dummy_dest_dir")

    @mock.patch("photo_id.get_size_data.logging.error")
    @mock.patch("photo_id.get_size_data.zipfile.ZipFile", side_effect=FileNotFoundError)
    def test_file_not_found(self, mock_zipfile, mock_log_error):
        with self.assertRaises(SystemExit):
            extract_file_from_zip("dummy_zip_path", "dummy_file_name", "dummy_dest_dir")
        mock_log_error.assert_called_once_with(
            "The file '%s' was not found.", "dummy_zip_path"
        )

    @mock.patch("photo_id.get_size_data.logging.error")
    @mock.patch("photo_id.get_size_data.zipfile.ZipFile")
    def test_file_not_in_zip(self, mock_zipfile, mock_log_error):
        mock_zip = mock_zipfile.return_value.__enter__.return_value
        mock_zip.extract.side_effect = KeyError
        with self.assertRaises(SystemExit):
            extract_file_from_zip("dummy_zip_path", "dummy_file_name", "dummy_dest_dir")
        mock_log_error.assert_called_once_with(
            "Error: The file '%s' does not exist in the ZIP archive.", "dummy_file_name"
        )

    @mock.patch("photo_id.get_size_data.logging.error")
    @mock.patch(
        "photo_id.get_size_data.zipfile.ZipFile", side_effect=zipfile.BadZipFile
    )
    def test_invalid_zip_file(self, mock_zipfile, mock_log_error):
        with self.assertRaises(SystemExit):
            extract_file_from_zip("dummy_zip_path", "dummy_file_name", "dummy_dest_dir")
        mock_log_error.assert_called_once_with(
            "The file '%s' is not a valid ZIP file.", "dummy_zip_path"
        )

    @mock.patch("photo_id.get_size_data.logging.error")
    @mock.patch(
        "photo_id.get_size_data.zipfile.ZipFile",
        side_effect=Exception("Unexpected error"),
    )
    def test_unexpected_error(self, mock_zipfile, mock_log_error):
        with self.assertRaises(SystemExit):
            extract_file_from_zip("dummy_zip_path", "dummy_file_name", "dummy_dest_dir")
        mock_log_error.assert_called_once_with(
            "An unexpected error occurred. Reason: %s", "Unexpected error"
        )


class TestWriteDictToJson(unittest.TestCase):

    @mock.patch("photo_id.get_size_data.open", new_callable=mock.mock_open)
    @mock.patch("photo_id.get_size_data.json.dump")
    @mock.patch("photo_id.get_size_data.logging.info")
    def test_successful_write(self, mock_log_info, mock_json_dump, mock_open):
        data = {"key": "value"}
        file_path = "dummy_path.json"

        write_dict_to_json(data, file_path)

        mock_open.assert_called_once_with(file_path, mode="wt", encoding="utf-8")
        mock_json_dump.assert_called_once_with(data, mock_open(), indent=4)
        mock_log_info.assert_called_once_with(
            "Dictionary successfully written to '%s'", file_path
        )

    @mock.patch("photo_id.get_size_data.open", side_effect=IOError("Mocked IOError"))
    @mock.patch("photo_id.get_size_data.logging.error")
    def test_io_error(self, mock_log_error, mock_open):
        data = {"key": "value"}
        file_path = "dummy_path.json"

        write_dict_to_json(data, file_path)

        mock_open.assert_called_once_with(file_path, mode="wt", encoding="utf-8")
        mock_log_error.assert_called_once_with(
            "Error: Failed to write to the file '%s'. Reason: %s",
            file_path,
            "Mocked IOError",
        )


class TestReadDictFromJson(unittest.TestCase):

    @mock.patch(
        "photo_id.get_size_data.open",
        new_callable=mock.mock_open,
        read_data='{"key": "value"}',
    )
    @mock.patch("photo_id.get_size_data.json.load")
    def test_successful_read(self, mock_json_load, mock_open):
        mock_json_load.return_value = {"key": "value"}
        result = read_dict_from_json("dummy_path")
        self.assertEqual(result, {"key": "value"})
        mock_open.assert_called_once_with("dummy_path", mode="rt", encoding="utf-8")
        mock_json_load.assert_called_once()

    @mock.patch("photo_id.get_size_data.open", side_effect=FileNotFoundError)
    @mock.patch("photo_id.get_size_data.logging.error")
    def test_file_not_found(self, mock_log_error, mock_open):
        result = read_dict_from_json("dummy_path")
        self.assertEqual(result, {})
        mock_log_error.assert_called_with(
            "Error: Failed to read the file '%s'. Reason: %s", "dummy_path", mock.ANY
        )

    @mock.patch(
        "photo_id.get_size_data.open",
        new_callable=mock.mock_open,
        read_data='{"key": "value"}',
    )
    @mock.patch(
        "photo_id.get_size_data.json.load",
        side_effect=json.JSONDecodeError("Expecting value", "doc", 0),
    )
    @mock.patch("photo_id.get_size_data.logging.error")
    def test_json_decode_error(self, mock_log_error, mock_json_load, mock_open):
        result = read_dict_from_json("dummy_path")
        self.assertEqual(result, {})
        mock_log_error.assert_called_with(
            "Error: Failed to decode JSON from the file '%s'. Reason: %s",
            "dummy_path",
            mock.ANY,
        )

    @mock.patch("photo_id.get_size_data.open", side_effect=IOError)
    @mock.patch("photo_id.get_size_data.logging.error")
    def test_io_error(self, mock_log_error, mock_open):
        result = read_dict_from_json("dummy_path")
        self.assertEqual(result, {})
        mock_log_error.assert_called_with(
            "Error: Failed to read the file '%s'. Reason: %s", "dummy_path", mock.ANY
        )


class TestGetNewAvonetData(unittest.TestCase):

    @mock.patch("photo_id.get_size_data.download_file")
    def test_successful_download(self, mock_download_file):
        # Call the function
        get_new_avonet_data()

        # Assert that download_file was called with the correct parameters
        mock_download_file.assert_called_once_with(
            "https://figshare.com/ndownloader/files/34480856", "temp/aviform_data.xlsx"
        )

    @mock.patch(
        "photo_id.get_size_data.download_file", side_effect=Exception("Download failed")
    )
    @mock.patch("photo_id.get_size_data.logging.error")
    def test_download_failure(self, mock_log_error, mock_download_file):
        with self.assertRaises(Exception):
            get_new_avonet_data()


class TestProcessAvonetData(unittest.TestCase):

    @mock.patch("photo_id.get_size_data.write_dict_to_json")
    @mock.patch("photo_id.get_size_data.read_xlsx_to_dict")
    def test_successful_processing(
        self, mock_read_xlsx_to_dict, mock_write_dict_to_json
    ):
        mock_data = {
            "SpeciesA": {"Wing.Length": 10.5, "Habitat": "Forest", "Mass": 1.2},
            "SpeciesB": {"Wing.Length": 12.3, "Habitat": "Desert", "Mass": 1.5},
        }
        mock_read_xlsx_to_dict.return_value = mock_data

        process_avonet_data()

        mock_read_xlsx_to_dict.assert_called_once_with(
            "temp/aviform_data.xlsx",
            "AVONET2_eBird",
            ["Species2", "Wing.Length", "Habitat", "Mass"],
        )
        mock_write_dict_to_json.assert_called_once_with(
            mock_data, "temp/aviform_data.json"
        )

    @mock.patch("photo_id.get_size_data.write_dict_to_json")
    @mock.patch(
        "photo_id.get_size_data.read_xlsx_to_dict", side_effect=Exception("Read error")
    )
    @mock.patch("photo_id.get_size_data.logging.error")
    def test_read_failure(
        self, mock_log_error, mock_read_xlsx_to_dict, mock_write_dict_to_json
    ):
        with self.assertRaises(Exception):
            process_avonet_data()

        mock_read_xlsx_to_dict.assert_called_once_with(
            "temp/aviform_data.xlsx",
            "AVONET2_eBird",
            ["Species2", "Wing.Length", "Habitat", "Mass"],
        )
        mock_write_dict_to_json.assert_not_called()


    @mock.patch(
        "photo_id.get_size_data.write_dict_to_json",
        side_effect=Exception("Write error"),
    )
    @mock.patch("photo_id.get_size_data.read_xlsx_to_dict")
    @mock.patch("photo_id.get_size_data.logging.error")
    def test_write_failure(
        self, mock_log_error, mock_read_xlsx_to_dict, mock_write_dict_to_json
    ):
        mock_data = {
            "SpeciesA": {"Wing.Length": 10.5, "Habitat": "Forest", "Mass": 1.2},
            "SpeciesB": {"Wing.Length": 12.3, "Habitat": "Desert", "Mass": 1.5},
        }
        mock_read_xlsx_to_dict.return_value = mock_data

        with self.assertRaises(Exception):
            process_avonet_data()

        mock_read_xlsx_to_dict.assert_called_once_with(
            "temp/aviform_data.xlsx",
            "AVONET2_eBird",
            ["Species2", "Wing.Length", "Habitat", "Mass"],
        )
        mock_write_dict_to_json.assert_called_once_with(
            mock_data, "temp/aviform_data.json"
        )



class TestReadCachedAvonetData(unittest.TestCase):

    @mock.patch(
        "photo_id.get_size_data.open",
        new_callable=mock.mock_open,
        read_data='{"SpeciesA": {"Wing.Length": 10.5, "Habitat": "Forest", "Mass": 1.2}}',
    )
    @mock.patch("photo_id.get_size_data.json.load")
    def test_successful_read(self, mock_json_load, mock_open):
        expected_data = {
            "SpeciesA": {"Wing.Length": 10.5, "Habitat": "Forest", "Mass": 1.2}
        }
        mock_json_load.return_value = expected_data

        result = read_cached_avonet_data()
        self.assertEqual(result, expected_data)

    @mock.patch("photo_id.get_size_data.open", side_effect=FileNotFoundError)
    @mock.patch("photo_id.get_size_data.logging.error")
    def test_file_not_found(self, mock_log_error, mock_open):
        result = read_cached_avonet_data()
        self.assertEqual(result, {})
        mock_log_error.assert_called_with(
            "Error: Failed to read the file '%s'. Reason: %s",
            "temp/aviform_data.json",
            mock.ANY,
        )

    @mock.patch(
        "photo_id.get_size_data.open",
        new_callable=mock.mock_open,
        read_data='{"invalid_json": ',
    )
    @mock.patch(
        "photo_id.get_size_data.json.load",
        side_effect=json.JSONDecodeError("Expecting value", "doc", 0),
    )
    @mock.patch("photo_id.get_size_data.logging.error")
    def test_json_decode_error(self, mock_log_error, mock_json_load, mock_open):
        result = read_cached_avonet_data()
        self.assertEqual(result, {})
        mock_log_error.assert_called_with(
            "Error: Failed to decode JSON from the file '%s'. Reason: %s",
            "temp/aviform_data.json",
            mock.ANY,
        )
