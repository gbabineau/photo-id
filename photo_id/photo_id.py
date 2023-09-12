"""
    Main function for the photo_id application which presents a quiz of bird photos based on a definition of species, and time of year (to handle different)
    plumages.
"""
import argparse
import logging

from tkinter import messagebox, Tk, Menu, filedialog
import get_taxonomy
import get_have_list
import image_window


class MainWindow:
    """Creates the main window from which quizzes can be launched."""

    def __init__(self, default_have_list : str):
        self.have_list=[]

        self.taxonomy=get_taxonomy.ebird_taxonomy()
        if default_have_list != '':
            self.have_list=get_have_list.get_have_list(default_have_list)
        self.root = Tk()
        self.root.title('Photo ID quiz')
        menubar = Menu(self.root)
        file_menu = Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Quiz", command=self.file_open)
        file_menu.add_command(label="Open Have List", command=self.have_list_open)
        file_menu.add_command(label="Save", command=self.donothing)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        help_menu = Menu(menubar, tearoff=0)
        help_menu.add_command(label="Help Index", command=self.donothing)
        help_menu.add_command(label="About...", command=self.donothing)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)
        self.root.mainloop()

    def file_open(self) -> None:
        """ Open and start a new quiz defined by a quiz file. """
        filename = filedialog.askopenfilename(
            title='Select a Quiz File', initialdir='.', filetypes=[('json files', '*.json')])
        image_window.ImageWindow(filename, self.taxonomy, self.have_list)


    def have_list_open(self) -> None:
        """ Open and start a new quiz defined by a quiz file. """
        filename = filedialog.askopenfilename(
            title='Select a Have List File', initialdir='.', filetypes=[('CSV files', '*.csv')])
        if filename != '':
            self.have_list=get_have_list.get_have_list(filename)


    def donothing(self) -> None:
        """ Placeholder for functions not yet implemented. """
        messagebox.showinfo(title='not implemented',
                            message='not implemented yet')

def main():
    """ Main function for the app. """
    arg_parser = argparse.ArgumentParser(
        prog='photo-id',
        description='Quiz on photo id.')
    arg_parser.add_argument(
        '--version', action='version', version='%(prog)s 0.0.0')
    arg_parser.add_argument(
        '--verbose', action='store_true', help='increase verbosity')
    arg_parser.add_argument(
        '--have_list',  default='', help='list of birds had for a region/time frame')
    args = arg_parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    MainWindow(args.have_list)


if __name__ == "__main__":
    main()
