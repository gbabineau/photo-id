"""
    Creates the image window
"""
import io
import logging
import random
import re

from tkinter import ttk, messagebox, Label, StringVar, Toplevel
import requests
from PIL import Image, ImageTk
import process_quiz

class ImageWindow:
    """Class representing an image window which can be instantiated multiple times """

    quiz_species = {}
    quiz_species_list = []

    def __init__(self, file: str, taxonomy: dict, have_list: list):
        self.root = Toplevel()
        self.have_list=have_list
        self.quiz_data = process_quiz.process_quiz_file(file, taxonomy)
        self.species_list = [d['comName']
                             for d in self.quiz_data['species'] if 'comName' in d]
        self.quiz_species = str(random.choice(self.species_list))

        # Create a photoimage object of the image in the path
        test = ImageTk.PhotoImage(self.get_image(
            self.quiz_species, self.quiz_data['location'], self.quiz_data['start_month'], self.quiz_data['end_month']))

        self.image_display = Label(self.root, image=test)
        self.image_display.image = test

        self.selected_species = StringVar(self.root)
        self.selected_species.set('')
        self.specific_species = StringVar(self.root)
        self.specific_species.set('')
        Label(self.root, text='Notes:'+self.quiz_data['notes']).grid(
            row=0, column=0)  # default value

        # row 1 buttons
        ttk.Button(self.root, text="Show a New Image of the Same Species",
                   command=self.update_image).grid(row=1, column=0)
        ttk.Button(self.root, text="Get a New Species",
                   command=self.get_new_random_species).grid(row=1, column=1)
        ttk.Button(self.root, text="Reveal what the species is",
                   command=self.reveal_species).grid(row=1, column=2)

        # row 2 buttons
        Label(self.root, text="What is this bird?").grid(
            row=2, column=0)  # default value
        self.what_is_it = ttk.Combobox(self.root, textvariable=self.selected_species,
                                       values=self.species_list, height=min(25, len(self.species_list)), width=30)
        self.what_is_it.bind('<<ComboboxSelected>>', self.check_selection)

        self.what_is_it.grid(row=2, column=1)
        self.have_bird=ttk.Label(self.root, text='have')
        self.have_bird.grid(row=2, column=2)
        style = ttk.Style()
        style.configure("BG.TLabel", background="green")
        style.configure("BW.TLabel", background="white")
        self.set_have_label()
        self.bird_notes=ttk.Label(self.root, text='None')
        self.bird_notes.grid(row=2, column=3)
        # row 3 buttons
        ttk.Label(self.root, text="Change to a specific bird.").grid(
            row=3, column=0)  # default value
        combobox = ttk.Combobox(self.root, textvariable=self.specific_species,
                                values=self.species_list, height=min(25, len(self.species_list)), width=30)
        combobox.bind('<<ComboboxSelected>>', self.picked_image)
        combobox.grid(row=3, column=1)
        # row 4 buttons

        self.image_display.grid(row=4, column=0, columnspan=8)
        self.set_bird_notes()

    def set_have_label(self) -> None:
        """ called to set indicator of whether this bird is on the have_list or not """
        found= next((item for item in self.have_list if item["name"] == self.quiz_species), False)

        if found:
            self.have_bird.config(text="Have it",style="BG.TLabel")
        else:
            self.have_bird.config(text="Don't have it",style="BW.TLabel")

    def check_selection(self, unused) -> None:
        """Called when a selection is made to see if it is the right species. The unused parameter is to match the signature used by the caller. """
        del unused
        if self.selected_species.get() == self.quiz_species:
            messagebox.showinfo(title='correct', message='Correct!')
            if len(self.species_list) > 1:
                self.species_list.remove(self.quiz_species)
                self.what_is_it.config(values=self.species_list)
                self.quiz_species = ''
                self.get_new_random_species()
            else:
                messagebox.showinfo(
                    title='completed', message='Congratulations - you completed the quiz!')
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
        messagebox.showinfo(
            title='reveal', message=f'This is a {self.quiz_species}')

    def get_image_list(self, species_code : str, location : str, start_month: int, end_month: int) -> list:
        """Gets list of images."""
        images = []
        if len(location) > 0:
            location=f"&regionCode={location}"
        if not (start_month==1 and end_month == 12):
            time=f"&beginMonth={start_month}&endMonth={end_month}"
        else:
            time=''
        get_string=f'https://media.ebird.org/catalog?view=grid&taxonCode={species_code}&sort=rating_rank_desc&mediaType=photo{location}{time}'
        result = requests.get(get_string, timeout=10)

        content = str(result.content)
        images = re.findall(
            r"https://cdn\.download\.ams\.birds\.cornell\.edu/api/v1/asset/\d+/1200", content)
        return images

    def get_image(self, species: str, location: str, start_month: int, end_month: int) -> None:
        """Gets a requested image and displays it."""
        # e.g. display_image('comchi1', 'NO', 6 )
        species_code = process_quiz.get_code(self.quiz_data, species)
        image_list = self.get_image_list(species_code, location, start_month, end_month)

        if len(image_list) <= 2:
            # Try looking at all locations
            logging.info(f'No images for {species} at given location and time')
            image_list = self.get_image_list(species_code, '', start_month, end_month)
            if len(image_list) <= 2:
                logging.info(f'No images for {species} at any location at given time')
                # Try looking at all times
                image_list = self.get_image_list(species_code, '', 1, 12)

        if len(image_list) > 2:
            image_number = random.randint(2, len(image_list)-1)
            img_bytes = requests.get(
                image_list[image_number], timeout=10).content
            image = Image.open(io.BytesIO(img_bytes))
        else:
            logging.error(f'No images for {species} at any location or time')
            image = Image.open('photo_id/resources/Banner__Under_Construction__version_2.jpg')

        return image

    def set_bird_notes(self) -> None:
        """Updates the bird notes field."""
        entry = next(item for item in self.quiz_data['species'] if item["comName"] == self.quiz_species)
        if entry is not None and 'notes' in entry.keys():
            note = entry['notes']
        else:
            note = ''
        self.bird_notes.configure(text=note)

    def update_image(self) -> None:
        """Updates the displayed image."""
        test2 = ImageTk.PhotoImage(self.get_image(
            self.quiz_species, self.quiz_data['location'], self.quiz_data['start_month'], self.quiz_data['end_month']))
        self.image_display.configure(image=test2)
        self.image_display.image = test2
        self.set_have_label()
        self.set_bird_notes()

    def get_new_random_species(self) -> None:
        """Gets a new species from the selected list. Tries to avoid getting the same species twice in a row."""
        self.selected_species.set('')
        without_current_species = self.species_list.copy()
        if self.quiz_species != '':
            without_current_species.remove(self.quiz_species)
        self.quiz_species = str(random.choice(without_current_species))
        self.update_image()