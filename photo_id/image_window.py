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
REQUIRED_IMAGES = 2*2
IMAGES_TO_USE = 12*2


class ImageWindow:
    """Class representing an image window which can be instantiated multiple times """

    quiz_species = {}
    quiz_species_list = []
    cached_species_code = ''
    cached_species_images = []

    def __init__(self, file: str, taxonomy: dict, have_list: list):
        self.root = Toplevel()
        self.have_list = have_list
        self.quiz_data = process_quiz.process_quiz_file(file, taxonomy)
        self.species_list = [d['comName']
                             for d in self.quiz_data['species'] if 'comName' in d]
        self.quiz_species = str(random.choice(self.species_list))
        self.image_number = 0
        # Create a photoimage object of the image in the path
        test = ImageTk.PhotoImage(self.get_image(
            self.quiz_species, self.quiz_data['location'], self.quiz_data['start_month'], self.quiz_data['end_month']))

        self.image_display = Label(self.root, image=test)
        self.image_display.image = test

        self.selected_species = StringVar(self.root)
        self.selected_species.set('')
        self.specific_species = StringVar(self.root)
        self.specific_species.set('')
        self.root.title(self.root.title()+' :'+file)

        Label(self.root, text='Notes:'+self.quiz_data['notes']).grid(
            row=0, column=0)  # default value

        # row 1 buttons
        ttk.Button(self.root, text="Show Next Image",
                   command=self.update_image).grid(row=1, column=0)
        ttk.Button(self.root, text="Show Prior Image",
                   command=self.prior_image).grid(row=1, column=1)

        ttk.Button(self.root, text="Get a New Species",
                   command=self.get_new_random_species).grid(row=1, column=2)
        ttk.Button(self.root, text="Reveal what the species is",
                   command=self.reveal_species).grid(row=1, column=3)

        # row 2 buttons
        Label(self.root, text="What is this bird?").grid(
            row=2, column=0)  # default value
        self.what_is_it = ttk.Combobox(self.root, textvariable=self.selected_species,
                                       values=self.species_list, height=min(25, len(self.species_list)), width=30)
        self.what_is_it.bind('<<ComboboxSelected>>', self.check_selection)

        self.what_is_it.grid(row=2, column=1)
        self.have_bird = ttk.Label(self.root, text='have')
        self.have_bird.grid(row=2, column=2)
        style = ttk.Style()
        style.configure("BG.TLabel", background="green")
        style.configure("BW.TLabel", background="white")
        self.set_have_label()
        self.bird_notes = ttk.Label(self.root, text='None')
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
        found = next(
            (item for item in self.have_list if item["comName"] == self.quiz_species), False)

        if found:
            self.have_bird.config(text="Have it", style="BG.TLabel")
        else:
            self.have_bird.config(text="Don't have it", style="BW.TLabel")

    def check_selection(self, unused) -> None:
        """Called when a selection is made to see if it is the right species. The unused parameter is to match the signature used by the caller. """
        del unused
        if self.selected_species.get() == self.quiz_species:
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
        self.selected_species.set('')
        self.quiz_species = self.specific_species.get()
        self.update_image()
        self.specific_species.set('')

    def reveal_species(self) -> None:
        """Called when the user asks to reveal what the species is."""
        messagebox.showinfo(
            title='reveal', message=f'This is a {self.quiz_species}')

    def get_image_list(self, species_code: str, location: str, start_month: int, end_month: int) -> list:
        """Gets list of images urls and caches them."""
        if self.cached_species_code != species_code:
            self.cached_species_images = []
            if len(location) > 0:
                location = f"&regionCode={location}"
            time = '' if start_month == 1 and end_month == 12 else f"&beginMonth={start_month}&endMonth={end_month}"
            get_string = f'https://media.ebird.org/catalog?view=grid&taxonCode={species_code}&sort=rating_rank_desc&mediaType=photo{location}{time}'
            result = requests.get(get_string, timeout=10)

            content = str(result.content)
            images = re.findall(
                r"https://cdn\.download\.ams\.birds\.cornell\.edu/api/v1/asset/\d+/1200", content)
            if len(images) > 2 + REQUIRED_IMAGES:  # First images are not actual images of the species.
                self.cached_species_images = images[2:]
                self.cached_species_code = species_code
                del self.cached_species_images[2*IMAGES_TO_USE:]

        return self.cached_species_images

    def get_image(self, species: str, location: str, start_month: int, end_month: int) -> None:
        """Gets a requested image and displays it."""
        # e.g. display_image('comchi1', 'NO', 6 )
        species_code = process_quiz.get_code(self.quiz_data, species)
        image_list = self.get_image_list(
            species_code, location, start_month, end_month)

        # Try to get multiple images - otherwise expand search to other locations and times
        if len(image_list) <= REQUIRED_IMAGES:
            # Try looking at all locations
            logging.info(f'Not enough images for {species} at given location and time')
            image_list = self.get_image_list(
                species_code, '', start_month, end_month)
            if len(image_list) <= REQUIRED_IMAGES:
                logging.info(
                    f'Not enough images for {species} at any location at given time')
                # Try looking at all times
                image_list = self.get_image_list(species_code, '', 1, 12)

        if len(image_list) > 0:
            # only use the first IMAGES_TO_USE (nominally highest rated images)
            if self.image_number >= min(len(image_list), IMAGES_TO_USE):
                self.image_number = 0
            img_bytes = requests.get(
                image_list[self.image_number], timeout=10).content
            image = Image.open(io.BytesIO(img_bytes))
            self.image_number = self.image_number+2
        else:
            logging.error(f'No images for {species} at any location or time')
            image = Image.open(
                'photo_id/resources/Banner__Under_Construction__version_2.jpg')

        return image

    def set_bird_notes(self) -> None:
        """Updates the bird notes field."""
        entry = next(
            item for item in self.quiz_data['species'] if item["comName"] == self.quiz_species)
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

    def prior_image(self) -> None:
        """Goes to the prior image."""
        if self.image_number < 4:
            self.image_number = IMAGES_TO_USE - 2
        else:
            self.image_number = self.image_number - 4
        self.update_image()

    def get_new_random_species(self) -> None:
        """Gets a new species from the selected list. Tries to avoid getting the same species twice in a row."""
        self.selected_species.set('')
        self.image_number = random.choice(range(0, IMAGES_TO_USE, 2))
        without_current_species = self.species_list.copy()
        if self.quiz_species != '' and self.quiz_species in self.species_list and len(self.quiz_species_list) > 1:
            without_current_species.remove(self.quiz_species)
        self.quiz_species = str(random.choice(without_current_species))
        self.update_image()
