"""
    Creates the image window
"""
import io
import logging
import random
import re

from tkinter import ttk, messagebox, Label, StringVar, Toplevel, Canvas
from tkinter.constants import VERTICAL, FALSE, RIGHT, LEFT, BOTH, TRUE, Y, NW, RIDGE

import requests
from PIL import Image, ImageTk
import process_quiz
import sys


REQUIRED_IMAGES = 2
IMAGES_TO_USE = 12


class VerticalScrolledFrame(ttk.Frame):
    """A pure Tkinter scrollable frame that actually works!
    * Use the 'interior' attribute to place widgets inside the scrollable frame.
    * Construct and pack/place/grid normally.
    * This frame only allows vertical scrolling.
    """

    def __init__(self, parent, *args, **kw):
        ttk.Frame.__init__(self, parent, *args, **kw)

        # Create a canvas object and a vertical scrollbar for scrolling it.
        vscrollbar = ttk.Scrollbar(self, orient=VERTICAL)
        vscrollbar.pack(fill=Y, side=RIGHT, expand=FALSE)
        canvas = Canvas(self, bd=0, highlightthickness=0,
                           yscrollcommand=vscrollbar.set)
        canvas.pack(side=LEFT, fill=BOTH, expand=TRUE)
        vscrollbar.config(command=canvas.yview)

        # Reset the view
        canvas.xview_moveto(0)
        canvas.yview_moveto(0)

        # Create a frame inside the canvas which will be scrolled with it.
        self.interior = interior = ttk.Frame(canvas)
        interior_id = canvas.create_window(0, 0, window=interior,
                                           anchor=NW)

        # Track changes to the canvas and frame width and sync them,
        # also updating the scrollbar.
        def _configure_interior(event):
            # Update the scrollbars to match the size of the inner frame.
            size = (interior.winfo_reqwidth(), interior.winfo_reqheight())
            canvas.config(scrollregion="0 0 %s %s" % size)
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # Update the canvas's width to fit the inner frame.
                canvas.config(width=interior.winfo_reqwidth())
        interior.bind('<Configure>', _configure_interior)

        def _configure_canvas(event):
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # Update the inner frame's width to fill the canvas.
                canvas.itemconfigure(interior_id, width=canvas.winfo_width())
        canvas.bind('<Configure>', _configure_canvas)

def scale_image_width(image):
    """
    Scales an image to a max size while preserving aspect ratio. Only the width matters.
    """
    MAX_X=460  # Make these parameters
    width, height = image.size
    new_width = MAX_X
    new_height = int((MAX_X/ width) * height)

    return image.resize(
        (new_width, new_height), Image.Resampling.LANCZOS)

class SpeciesFrame(ttk.Frame):

    def __init__(self, base, species_number : int, species_name : str, species_code : str, species_notes : str, large_species_list : list, location : str, start_month : str, end_month : str):
        ttk.Frame.__init__(self, base, borderwidth=2, relief=RIDGE)
        self.species_number = species_number
        self.species_code = species_code
        self.species_name = species_name
        self.location = location
        self.start_month = start_month
        self.end_month = end_month
        self.image_number = 0
        self.selected_species = StringVar(self)
        self.selected_species.set('')
        self.image_display = Label(self)
        self.full_species_list=large_species_list
        self.cached_image_list = []

        self.update_image()

        self.what_is_it = ttk.Combobox(self, textvariable=self.selected_species,
                                       values=self.species_list, height=min(25, len(self.species_list)), width=30)
        self.what_is_it.bind('<<ComboboxSelected>>', self.check_selection)

        self.what_is_it.grid(row=0, column=0)
        ttk.Button(self, text="Next",
                   command=self.next_image).grid(row=0, column=2)
        ttk.Button(self, text="Prior",
                   command=self.prior_image).grid(row=0, column=1)
        self.bird_notes = ttk.Label(self, text=species_notes)
        self.bird_notes.grid(row=1, column=0)
        self.image_display.grid(row=2, column=0, columnspan=3)

    def update_image(self) -> None:
        position_in_list = self.full_species_list.index(self.species_name)
        choices = 7
        choices = min(len(self.full_species_list), choices)
        choice=random.randrange(choices)
        if position_in_list+choices >= len(self.full_species_list):
            first = max(0, position_in_list-choices+1)
        elif position_in_list >= choice:
            first = position_in_list - choice
        elif position_in_list == 0:
            first = 0
        else:
            first = random.randrange(position_in_list)
        self.species_list = self.full_species_list[first:first+choices]
        # Doing this rather than shuffling the whole thing...because it is kind of nice to have the images taxonomically but then
        # if the choices are ordered taxonomically it is too easy
        random.shuffle(self.species_list)
        image = self.get_image(self.species_code, self.location, self.start_month, self.end_month)
        image = scale_image_width(image)
        tk_image = ImageTk.PhotoImage(image)
        self.image_display.configure(image=tk_image)
        self.image_display.image = tk_image


    def check_selection(self, unused) -> None:
        """Called when a selection is made to see if it is the right species. The unused parameter is to match the signature used by the caller. """
        del unused
        if self.selected_species.get() != self.species_name:
            messagebox.showerror(title='incorrect', message='Try again!')


    def next_image(self):
        if self.image_number < min(len(self.cached_image_list), IMAGES_TO_USE) -1:
            self.image_number = self.image_number+1
        else:
            self.image_number = 0
        self.update_image()

    def prior_image(self):
        if self.image_number == 0:
            self.image_number = min(len(self.cached_image_list), IMAGES_TO_USE)
        else:
            self.image_number = self.image_number -1
        self.update_image()

    def get_image_list(self, species_code: str, location: str, start_month: int, end_month: int) -> list:
        """Gets list of images urls."""
        if self.cached_image_list == []:
            if len(location) > 0:
                location = f"&regionCode={location}"
            time = '' if start_month == 1 and end_month == 12 else f"&beginMonth={start_month}&endMonth={end_month}"
            get_string = f'https://media.ebird.org/catalog?view=grid&taxonCode={species_code}&sort=rating_rank_desc&mediaType=photo{location}{time}'
            for retries in range(5):
                try:
                    result = requests.get(get_string, timeout=20)
                    result.raise_for_status()
                    break
                except requests.exceptions.RequestException as e:
                    logging.warning(f'Get failed with {e}')
                    if retries == 4:
                        sys.exit(1)

            content = str(result.content)
            images = re.findall(
                r"https://cdn\.download\.ams\.birds\.cornell\.edu/api/v1/asset/\d+/1200", content)
            # First images are not actual images of the species.
            if len(images) > 2 + REQUIRED_IMAGES:
                self.cached_image_list = images[2::2]
                del self.cached_image_list[IMAGES_TO_USE:]
        return self.cached_image_list

    def get_image(self, species_code: str, location: str, start_month: int, end_month: int) -> None:
        """Gets a requested image and displays it."""
        # e.g. display_image('comchi1', 'NO', 6 )
        image_list = self.get_image_list(
            species_code, location, start_month, end_month)

        # Try to get multiple images - otherwise expand search to other locations and times
        if len(image_list) <= REQUIRED_IMAGES:
            # Try looking at all locations
            logging.info(
                f'Not enough images for {species_code} at given location and time')
            image_list = self.get_image_list(
                species_code, '', start_month, end_month)
            if len(image_list) <= REQUIRED_IMAGES:
                logging.info(
                    f'Not enough images for {species_code} at any location at given time')
                # Try looking at all times
                image_list = self.get_image_list(species_code, '', 1, 12)

        if len(image_list) > 0:
            try:
                result = requests.get(
                    image_list[self.image_number], timeout=10)
                result.raise_for_status()
            except requests.exceptions.RequestException as e:
                logging.warning(f'Get failed with {e}')
            img_bytes = result.content
            image = Image.open(io.BytesIO(img_bytes))
        else:
            logging.error(f'No images for {species_code} at any location or time')
            image = Image.open(
                'photo_id/resources/Banner__Under_Construction__version_2.jpg')

        return image


class MatchWindow:
    """Class representing a match window which can be instantiated multiple times """

    quiz_species = {}
    quiz_species_list = []


    def __init__(self, file: str, taxonomy: dict, have_list: list):
        self.root = Toplevel()
        self.have_list = have_list
        self.quiz_data = process_quiz.process_quiz_file(file, taxonomy)
        self.species_list = [d['comName']
                             for d in self.quiz_data['species'] if 'comName' in d]

        Label(self.root, text='Notes:'+self.quiz_data['notes']).pack()  # default value
        COLUMNS=4
        ROWS = int(len(self.species_list) / COLUMNS) +1
        # COLUMNS =1
        # ROWS = 3
        logging.debug("lines above for testing fast")

        # Create a photoimage object of the image in the path

        self.image_display = [[None for x in range(COLUMNS)] for y in range(ROWS+1)]
        self.frame = VerticalScrolledFrame(self.root)
        # self.frame.grid(row=1, column=0)
        self.frame.pack(fill="both", expand=1)

        self.root.title(self.root.title()+' :'+file)
        species_number=0
        # progressbar = ttk.Progressbar(self.root, maximum=len(self.species_list))
        # progressbar.pack()
        for row in range(1,ROWS+1):
            for column in range(COLUMNS):
                # progressbar.step(species_number)
                logging.info(f'Processing image {species_number} of {len(self.species_list)}')
                if species_number >= len(self.species_list):
                    break
                species_name=self.species_list[species_number]
                species_code=process_quiz.get_code(self.quiz_data, species_name)
                species_notes = process_quiz.get_notes(
                    self.quiz_data, species_name)
                self.image_display[row][column] = SpeciesFrame(
                    self.frame.interior, species_number, species_name, species_code, species_notes, self.species_list, self.quiz_data['location'], self.quiz_data['start_month'], self.quiz_data['end_month'])
                self.image_display[row][column].grid(
                    row=row, column=column)
                species_number = species_number + 1

            if species_number >= len(self.species_list):
                break
        logging.info(f'Finished processing images')
        self.root.state('zoomed')


