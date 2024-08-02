"""
    Main function for the photo_id application which presents a quiz of bird photos
    based on a definition of species, and time of year (to handle different)
    plumages.
"""

import argparse
import logging

from tkinter import messagebox, Tk, Menu, filedialog, simpledialog
from photo_id import get_taxonomy
from photo_id import get_have_list
from photo_id import get_size_data
from photo_id import match_window
from photo_id import process_quiz


class MainWindow:
    """Creates the main window from which quizzes can be launched."""

    json_files = ("json files", "*.json")

    def __init__(self, default_have_list: str):
        self.have_list = []
        self.avonet_data = {}
        self.taxonomy = get_taxonomy.ebird_taxonomy()
        if default_have_list != "":
            self.have_list = get_have_list.get_have_list(default_have_list)
        self.root = Tk()
        self.root.title("Photo ID quiz")
        menubar = Menu(self.root)
        file_menu = Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Group Photos Quiz", command=self.match_open)
        file_menu.add_separator()
        file_menu.add_command(label="Open Have List", command=self.have_list_open)
        file_menu.add_separator()
        file_menu.add_command(label="Taxonomic Sort Quiz", command=self.sort_quiz)
        file_menu.add_command(
            label="Create Quiz List from Target Species", command=self.create_quiz
        )
        file_menu.add_command(
            label="Break Quiz into Parts", command=self.break_quiz_into_parts
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Refresh Avonet data", command=get_size_data.get_new_avonet_data
        )
        file_menu.add_command(
            label="Process Avonet data", command=get_size_data.process_avonet_data
        )
        file_menu.add_command(
            label="Read Cached Avonet data", command=self.read_avonet_data
        )
        file_menu.add_command(label="Add Avonet data to quiz(s)",
                              command=self.apply_avonet_data_to_quizzes)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        help_menu = Menu(menubar, tearoff=0)
        help_menu.add_command(label="Help Index", command=self.donothing)
        help_menu.add_command(label="About...", command=self.donothing)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)
        self.root.mainloop()

    def match_open(self) -> None:
        """Open and start a new matching game defined by a quiz file."""
        filename = filedialog.askopenfilename(
            title="Select a Quiz File", initialdir=".", filetypes=[self.json_files]
        )
        if filename != "":
            match_window.MatchWindow(filename, self.taxonomy, self.have_list)

    def sort_quiz(self) -> None:
        """Open a quiz, sort it taxonomically, and write it back. This is not necessary to show
        sorted quizzes during the game but can be useful with a long quiz if you want to break
        it into parts."""
        filename = filedialog.askopenfilename(
            title="Select a Quiz File", initialdir=".", filetypes=[self.json_files]
        )
        if filename != "":
            process_quiz.sort_quiz(filename, self.taxonomy)

    def read_avonet_data(self) -> None:
        """  Read the avonet data from the cache file."""
        self.avonet_data = get_size_data.read_cached_avonet_data()

    def create_quiz(self) -> None:
        """Create a quiz from a cut and paste of the target species list like
        https://ebird.org/targets?region=Oslo%2C+Norway+%28NO%29&r1=NO-03&bmo=5&emo=6&r2=NO-03&t2=day&mediaType=
        Note that reading from the website itself didn't work.
        """

        in_file = filedialog.askopenfilename(
            title="Select target file",
            initialdir=".",
            filetypes=[("text files", "*.txt")],
        )
        if in_file is not None:
            min_percent = simpledialog.askinteger(
                "min_percent", "Enter minimum percentage observed to include in quiz"
            )
            filename = filedialog.asksaveasfilename(
                title="Create Quiz as",
                initialdir=".",
                filetypes=[self.json_files],
                defaultextension=".json",
            )
            start_month = simpledialog.askinteger(
                "Starting Month", "Enter starting month 1-12", minvalue=1, maxvalue=12
            )
            end_month = simpledialog.askinteger(
                "Ending Month", "Enter ending month 1-12", minvalue=1, maxvalue=12
            )
            location_code = simpledialog.askstring(
                "2 letter location code", "Enter 2 letter location code"
            )
            if filename is not None:
                process_quiz.build_quiz_from_target_species(
                    in_file,
                    min_percent,
                    filename,
                    start_month,
                    end_month,
                    location_code,
                )

    def have_list_open(self) -> None:
        """Open and start a new quiz defined by a quiz file."""
        filename = filedialog.askopenfilename(
            title="Select a Have List File",
            initialdir=".",
            filetypes=[("CSV files", "*.csv")],
        )
        if filename != "":
            self.have_list = get_have_list.get_have_list(filename)

    def break_quiz_into_parts(self) -> None:
        """Open and start a new quiz defined by a quiz file."""
        filename = filedialog.askopenfilename(
            title="Select a Quiz File to break into parts",
            initialdir=".",
            filetypes=[self.json_files],
        )
        if filename != "":
            process_quiz.split_quiz(filename, 25, self.taxonomy)

    def apply_avonet_data_to_quizzes(self) -> None:
        """Apply avonet data to quizzes."""
        if self.avonet_data == {}:
            self.avonet_data = get_size_data.read_cached_avonet_data()

        filenames = filedialog.askopenfilenames(
            title="Select Quiz File (s) to apply avonet data",
            initialdir=".",
            filetypes=[self.json_files],
        )
        for filename in filenames:
            process_quiz.apply_avonet_data(filename, self.avonet_data)

    def donothing(self) -> None:
        """Placeholder for functions not yet implemented."""
        messagebox.showinfo(title="not implemented", message="not implemented yet")


def main():
    """Main function for the app."""
    arg_parser = argparse.ArgumentParser(
        prog="photo-id", description="Quiz on photo id."
    )
    arg_parser.add_argument("--version", action="version", version="%(prog)s 0.0.0")
    arg_parser.add_argument("--verbose", action="store_true", help="increase verbosity")
    arg_parser.add_argument(
        "--have_list", default="", help="list of birds had for a region/time frame"
    )
    args = arg_parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    MainWindow(args.have_list)


if __name__ == "__main__":
    main()
