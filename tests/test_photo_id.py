import logging
import unittest
from unittest.mock import patch, MagicMock
from photo_id.photo_id import MainWindow


class MockFrame(MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.children = {"!canvas": MagicMock(), "!scrollbar": MagicMock()}
        self.interior = MagicMock()


class MockRoot(MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "title"


class MockTK(MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.root = MockRoot()

    def title(self, title):
        pass  # do nothing

    def quit(self):
        pass  # do nothing

    def destroy(self):
        pass  # do nothing

    def config(self, menu):
        pass  # do nothing

    def mainloop(self, menu):
        pass  # do nothing


class MockMenu(MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_command(self, label, command):
        pass  # do nothing

    def add_cascade(self, label, menu):
        pass  # do nothing

    def add_separator(self):
        pass  # do nothing


class TestMainWindow(unittest.TestCase):
    @patch(
        "photo_id.photo_id.get_taxonomy.ebird_taxonomy", return_value=["taxa"]
    )
    @patch(
        "photo_id.photo_id.get_have_list.get_have_list", return_value=["have"]
    )
    @patch("photo_id.photo_id.Tk", spec=MockTK)
    @patch("photo_id.photo_id.Menu", spec=MockMenu)
    def setUp(self, mock_menu, mock_tk, mock_get_have_list, mock_get_taxonomy):
        self.main_window = MainWindow("test_have_list.csv")

    def tearDown(self):
        self.main_window.root.destroy()

    def test_initialization(self):
        self.assertEqual(self.main_window.have_list, ["have"])
        self.assertEqual(self.main_window.taxonomy, ["taxa"])

    @patch(
        "photo_id.photo_id.filedialog.askopenfilename",
        return_value="test_quiz.json",
    )
    @patch("photo_id.photo_id.match_window.MatchWindow")
    def test_match_open(self, mock_match_window, mock_askopenfilename):
        self.main_window.match_open()
        mock_match_window.assert_called_once_with(
            "test_quiz.json", unittest.mock.ANY, unittest.mock.ANY
        )

    @patch(
        "photo_id.photo_id.filedialog.askopenfilename",
        return_value="test_quiz.json",
    )
    @patch("photo_id.photo_id.process_quiz.sort_quiz")
    def test_sort_quiz(self, mock_sort_quiz, mock_askopenfilename):
        self.main_window.sort_quiz()
        mock_sort_quiz.assert_called_once_with(
            "test_quiz.json", unittest.mock.ANY
        )

    @patch(
        "photo_id.photo_id.filedialog.askopenfilename",
        return_value="test_target.txt",
    )
    @patch(
        "photo_id.photo_id.simpledialog.askinteger", side_effect=[10, 1, 12]
    )
    @patch("photo_id.photo_id.simpledialog.askstring", return_value="NO")
    @patch(
        "photo_id.photo_id.filedialog.asksaveasfilename",
        return_value="test_quiz.json",
    )
    @patch("photo_id.photo_id.process_quiz.build_quiz_from_target_species")
    def test_create_quiz(
        self,
        mock_build_quiz,
        mock_asksaveasfilename,
        mock_askstring,
        mock_askinteger,
        mock_askopenfilename,
    ):
        self.main_window.create_quiz()
        mock_build_quiz.assert_called_once_with(
            "test_target.txt", 10, "test_quiz.json", 1, 12, "NO"
        )

    @patch(
        "photo_id.photo_id.filedialog.askopenfilename",
        return_value="test_have_list.csv",
    )
    @patch(
        "photo_id.photo_id.get_have_list.get_have_list",
        return_value=["species1", "species2"],
    )
    def test_have_list_open(self, mock_get_have_list, mock_askopenfilename):
        self.main_window.have_list_open()
        self.assertEqual(self.main_window.have_list, ["species1", "species2"])

    @patch(
        "photo_id.photo_id.filedialog.askopenfilename",
        return_value="test_quiz.json",
    )
    @patch("photo_id.photo_id.process_quiz.split_quiz")
    def test_break_quiz_into_parts(
        self, mock_split_quiz, mock_askopenfilename
    ):
        self.main_window.break_quiz_into_parts()
        mock_split_quiz.assert_called_once_with(
            "test_quiz.json", 25, unittest.mock.ANY
        )

    @patch("photo_id.photo_id.messagebox.showinfo")
    def test_donothing(self, mock_showinfo):
        self.main_window.donothing()
        mock_showinfo.assert_called_once_with(
            title="not implemented", message="not implemented yet"
        )


class TestMainFunction(unittest.TestCase):
    @patch("photo_id.photo_id.MainWindow")
    @patch("photo_id.photo_id.argparse.ArgumentParser")
    def test_main_default(self, mock_arg_parser, mock_main_window):
        # Setup mock for argparse
        mock_args = MagicMock()
        mock_args.verbose = False
        mock_args.have_list = ""
        mock_arg_parser.return_value.parse_args.return_value = mock_args

        # Call the main function
        from photo_id.photo_id import main

        main()

        # Assertions
        mock_arg_parser.return_value.parse_args.assert_called_once()
        mock_main_window.assert_called_once_with("")

    @patch("photo_id.photo_id.MainWindow")
    @patch("photo_id.photo_id.argparse.ArgumentParser")
    @patch("photo_id.photo_id.logging.basicConfig")
    def test_main_verbose(
        self, mock_logging, mock_arg_parser, mock_main_window
    ):
        # Setup mock for argparse
        mock_args = MagicMock()
        mock_args.verbose = True
        mock_args.have_list = ""
        mock_arg_parser.return_value.parse_args.return_value = mock_args

        # Call the main function
        from photo_id.photo_id import main

        main()

        # Assertions
        mock_arg_parser.return_value.parse_args.assert_called_once()
        mock_logging.assert_called_once_with(level=logging.INFO)
        mock_main_window.assert_called_once_with("")

    @patch("photo_id.photo_id.MainWindow")
    @patch("photo_id.photo_id.argparse.ArgumentParser")
    def test_main_have_list(self, mock_arg_parser, mock_main_window):
        # Setup mock for argparse
        mock_args = MagicMock()
        mock_args.verbose = False
        mock_args.have_list = "test_have_list.csv"
        mock_arg_parser.return_value.parse_args.return_value = mock_args

        # Call the main function
        from photo_id.photo_id import main

        main()

        # Assertions
        mock_arg_parser.return_value.parse_args.assert_called_once()
        mock_main_window.assert_called_once_with("test_have_list.csv")
