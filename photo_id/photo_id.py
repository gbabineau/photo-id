"""
    Main function for the photo_id application which presents a quiz of bird photos based on a definition of species, and time of year (to handle different)
    plumages.
"""
import argparse
import io
import logging
import random
import re

from tkinter import ttk, messagebox, Tk, Label, StringVar, Menu, Toplevel, filedialog
import requests
from PIL import Image, ImageTk
import processQuiz


class ImageWindow:
    """Class representing an image window which can be instantiated multiple times """

    quiz_species = {}
    quiz_species_list=[]

    def __init__(self, file : str):
        self.root=Toplevel()
        self.quiz_data=processQuiz.process_quiz_file(file)
        self.species_list=[d['comName'] for d in self.quiz_data['species'] if 'comName' in d]
        self.quiz_species=str(random.choice(self.species_list))


        # Create a photoimage object of the image in the path
        test = ImageTk.PhotoImage(self.get_image(self.quiz_species, self.quiz_data['location'], self.quiz_data['start_month'],self.quiz_data['end_month']))

        self.image_display = Label(self.root, image=test)
        self.image_display.image = test

        self.selected_species = StringVar(self.root)
        self.selected_species.set('')
        self.specific_species =StringVar(self.root)
        self.specific_species.set('')
        # row 0 buttons
        ttk.Button(self.root, text="Show a New Image of the Same Species", command=self.update_image).grid(row=0, column=0)
        ttk.Button(self.root, text="Get a New Species", command=self.get_new_random_species).grid(row=0, column=1)
        ttk.Button(self.root, text="Reveal what the species is", command=self.reveal_species).grid(row=0, column=2)
        # row 1 buttons
        ttk.Label(self.root, text="What is this bird?").grid(row=1, column=0)# default value
        self.what_is_it = ttk.Combobox(self.root, textvariable=self.selected_species, values=self.species_list, height=min(25,len(self.species_list)), width=30)
        self.what_is_it.bind('<<ComboboxSelected>>', self.check_selection)
        self.what_is_it.grid(row=1, column=1)
        # row 2 buttons
        ttk.Label(self.root, text="Change to a specific bird.").grid(row=2, column=0)# default value
        combobox = ttk.Combobox(self.root, textvariable=self.specific_species, values=self.species_list, height=min(25,len(self.species_list)), width=30)
        combobox.bind('<<ComboboxSelected>>', self.picked_image)
        combobox.grid(row=2, column=1)
        # row 3 buttons

        self.image_display.grid(row=3, column=0, columnspan=8)

    def check_selection(self, unused) -> None:
        """Called when a selection is made to see if it is the right species. The unused parameter is to match the signature used by the caller. """
        del unused
        if self.selected_species.get() == self.quiz_species:
            messagebox.showinfo(title='correct', message='Correct!')
            if len(self.species_list) > 1:
                self.species_list.remove(self.quiz_species)
                self.what_is_it.config(values=self.species_list)
                self.quiz_species=''
                self.get_new_random_species()
            else:
                messagebox.showinfo(title='completed', message='Congratulations - you completed the quiz!')
                self.root.destroy()

        else:
            messagebox.showerror(title='incorrect', message='Try again!')

    def picked_image(self, unused) -> None:
        """Called when the user asks to see a specific species. The unused parameter is to match the signature used by the caller. """
        del unused
        self.quiz_species = self.specific_species.get()
        self.update_image()
        self.specific_species.set('')

    def reveal_species(self) -> None:
        """Called when the user asks to reveal what the species is."""
        messagebox.showinfo(title='reveal', message=f'This is a {self.quiz_species}')

    def get_image(self, species : str, location : str, start_month : int, end_month : int) -> None:
        """Gets a requested image and displays it."""
        # e.g. display_image('comchi1', 'NO', 6 )
        species_code=processQuiz.get_code(self.quiz_data, species)
        result=requests.get(f'https://media.ebird.org/catalog?view=grid&taxonCode={species_code}&sort=rating_rank_desc&mediaType=photo&regionCode={location}&beginMonth={start_month}&endMonth={end_month}', timeout = 10)

        content = str(result.content)
        image_list =re.findall (r"https://cdn\.download\.ams\.birds\.cornell\.edu/api/v1/asset/\d+/1200", content)
        if len(image_list) > 2:
            image_number=random.randint(2,len(image_list)-1)
            img_bytes = requests.get(image_list[image_number], timeout = 10).content
            return Image.open(io.BytesIO(img_bytes))
        else:
            logging.error(f'No images for {self.quiz_species} at time and location')
            return Image.open('photo_id/resources/Banner__Under_Construction__version_2.jpg')

    def update_image(self) -> None:
        """Updates the displayed image."""
        test2 = ImageTk.PhotoImage(self.get_image(self.quiz_species, self.quiz_data['location'], self.quiz_data['start_month'], self.quiz_data['end_month']))
        self.image_display.configure(image=test2)
        self.image_display.image = test2

    def get_new_random_species(self) -> None:
        """Gets a new species from the selected list. Tries to avoid getting the same species twice in a row."""
        self.selected_species.set('')
        without_current_species=self.species_list.copy()
        if self.quiz_species != '':
            without_current_species.remove(self.quiz_species)
        self.quiz_species=str(random.choice(without_current_species))
        self.update_image()

class MainWindow:
    """Creates the main window from which quizzes can be launched."""

    def __init__(self):

        self.root = Tk()
        self.root.title('Photo ID quiz')
        #self.root.geometry('1200x1300')
        menubar = Menu(self.root)
        file_menu = Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Quiz", command=self.file_open)
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
        filename = filedialog.askopenfilename(title='Select a Quiz File', initialdir='.',filetypes=[('json files', '*.json')])
        ImageWindow(filename)

    def donothing(self) -> None:
        """ Placeholder for functions not yet implemented. """
        messagebox.showinfo(title='not implemented', message='not implemented yet')


def main():
    """ Main function for the app. """
    arg_parser = argparse.ArgumentParser(
        description='Quiz on photo id.')
    arg_parser.add_argument(
        '--version', action='version', version='%(prog)s 0.0.0')
    arg_parser.add_argument(
        '--verbose', action='store_true', help='increase verbosity')


    args = arg_parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    MainWindow()



if __name__ == "__main__":
    main()
