"""
Creates the image window
"""

import io
import logging
import random
import re
import webbrowser

from tkinter import (
    ttk,
    Label,
    StringVar,
    Toplevel,
    Canvas,
    Message,
    Scrollbar,
    Button,
)
from tkinter.constants import (
    VERTICAL,
    FALSE,
    RIGHT,
    LEFT,
    BOTH,
    TRUE,
    Y,
    NW,
    RIDGE,
)

import requests
from PIL import Image, ImageTk
from photo_id import process_quiz
import sys


REQUIRED_IMAGES = 2
IMAGES_TO_USE = 12
MAX_WIDTH = 460  # Make this a function of the screen size


class VerticalScrolledFrame(ttk.Frame):
    """A Tkinter scrollable frame
    * Use the 'interior' attribute to place widgets inside the scrollable frame.
    * Construct and pack/place/grid normally.
    * This frame only allows vertical scrolling.
    """

    def __init__(self, parent, *args, **kw):
        ttk.Frame.__init__(self, parent, *args, **kw)

        # Create a canvas object and a vertical scrollbar for scrolling it.
        vscrollbar = Scrollbar(self, orient=VERTICAL)
        vscrollbar.pack(fill=Y, side=RIGHT, expand=FALSE)
        canvas = Canvas(
            self, bd=0, highlightthickness=0, yscrollcommand=vscrollbar.set
        )
        canvas.pack(side=LEFT, fill=BOTH, expand=TRUE)
        vscrollbar.config(command=canvas.yview)

        # Reset the view
        canvas.xview_moveto(0)
        canvas.yview_moveto(0)

        # Create a frame inside the canvas which will be scrolled with it.
        self.interior = interior = ttk.Frame(canvas)
        interior_id = canvas.create_window(0, 0, window=interior, anchor=NW)

        # Track changes to the canvas and frame width and sync them,
        # also updating the scrollbar.
        def _configure_interior(_event):
            # Update the scrollbars to match the size of the inner frame.
            size = (interior.winfo_reqwidth(), interior.winfo_reqheight())
            canvas.config(scrollregion="0 0 %s %s" % size)
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # Update the canvas's width to fit the inner frame.
                canvas.config(width=interior.winfo_reqwidth())

        interior.bind("<Configure>", _configure_interior)

        def _configure_canvas(_event):
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # Update the inner frame's width to fill the canvas.
                canvas.itemconfigure(interior_id, width=canvas.winfo_width())

        canvas.bind("<Configure>", _configure_canvas)


def web_browser_callback(url):
    """
    Opens a new web browser window with the specified URL.

    Args:
        url (str): The URL to open in the web browser.
    """
    webbrowser.open_new(url)


class SpeciesFrame(ttk.Frame):
    """
    A frame dedicated to displaying species information, including images and details.

    """

    def __init__(
        self,
        base,
        species_number: int,
        large_species_list: list,
        location: str,
        start_month: str,
        end_month: str,
        image_width: int,
    ):
        ttk.Frame.__init__(self, base, borderwidth=2, relief=RIDGE)
        species_data = large_species_list[species_number]

        self.species_code = species_data.get("speciesCode", "")
        self.species_name = species_data.get("comName", "")
        species_frequency = species_data.get("frequency", -1)
        species_notes = species_data.get("notes", "")
        self.location = location
        self.start_month = start_month
        self.end_month = end_month
        self.image_number = 0
        self.selected_species = StringVar(self)
        self.selected_species.set("")
        self.image_display = Label(self)
        self.full_species_list = large_species_list
        self.cached_image_list = []
        self.image_width = image_width

        self.update_image()
        # Now create a short list of species to select from

        position_in_list = species_number
        choices = min(len(self.full_species_list), 7)
        choice = random.randrange(choices)

        if position_in_list + choices >= len(self.full_species_list):
            first = max(0, position_in_list - choices + 1)
        elif position_in_list >= choice:
            first = position_in_list - choice
        elif position_in_list == 0:
            first = 0
        else:
            first = random.randrange(position_in_list)

        species_list = self.full_species_list[first : first + choices]
        # Opting for this method over shuffling the entire list to maintain
        # a taxonomic order. This makes the selection less predictable.
        random.shuffle(species_list)

        common_names = [species.get("comName", "") for species in species_list]
        self.what_is_it = ttk.Combobox(
            self,
            textvariable=self.selected_species,
            values=common_names,
            height=min(25, len(common_names)),
            width=30,
        )
        self.what_is_it.bind("<<ComboboxSelected>>", self.check_selection)
        current_row = 0
        self.what_is_it.grid(row=current_row, column=0)
        Button(self, text="Next", command=self.next_image).grid(
            row=current_row, column=2
        )
        Button(self, text="Prior", command=self.prior_image).grid(
            row=current_row, column=1
        )
        current_row = current_row + 1
        if species_frequency > 0:
            self.bird_frequency = Label(
                self,
                text=f"Frequency: {species_frequency:.2f}%",
                justify="left",
            )
            self.bird_frequency.grid(row=current_row, column=0)
            current_row = current_row + 1
        if species_notes != "":
            self.bird_notes = Label(
                self,
                text=f"Notes: {species_notes}",
                wraplength=int(self.image_width * 0.6),
                justify="left",
            )
            self.bird_notes.grid(row=current_row, column=0)
            current_row = current_row + 1
        if species_data.get("Habitat", "") != "":
            self.habitat = Label(
                self, text=f"Habitat: {species_data['Habitat']}"
            )
            self.habitat.grid(row=current_row, column=0)
        if species_data.get("Wing.Length", "") != "":
            self.habitat = Label(
                self, text=f"Wing Length: {species_data['Wing.Length']} mm"
            )
            self.habitat.grid(row=current_row, column=1)
        current_row = current_row + 1
        link1 = Label(
            self,
            text="Species Description on eBird",
            fg="blue",
            cursor="hand2",
        )
        link1.grid(row=current_row, column=0)
        link1.bind(
            "<Button-1>",
            lambda e: web_browser_callback(
                f"https://ebird.org/species/{self.species_code}"
            ),
        )
        current_row = current_row + 1

        self.image_display.grid(row=current_row, column=0, columnspan=3)

    def scale_image_width(self, image):
        """
        Scales an image to a max size while preserving aspect ratio. Only the width matters.
        """
        width, height = image.size
        new_width = self.image_width
        new_height = int((self.image_width / width) * height)

        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def update_image(self) -> None:
        """Updates the image displayed in the frame."""

        image = self.get_image(
            self.species_code, self.location, self.start_month, self.end_month
        )
        image = self.scale_image_width(image)
        tk_image = ImageTk.PhotoImage(image)
        self.image_display.configure(image=tk_image)
        self.image_display.image = tk_image

    def check_selection(self, unused) -> None:
        """Check a selection to see if it is the right species."""

        del unused
        if self.selected_species.get() != self.species_name:
            self.selected_species.set("")
            self.bell()
            top = Toplevel()
            top.title("Feedback")
            Message(top, text="Incorrect. Try again.", padx=20, pady=20).pack()
            top.after(1500, top.destroy)

    def next_image(self):
        """
        Advances to the next image in the cached list. If the end of the list is reached,
        it loops back to the first image.
        """
        self.image_number = (self.image_number + 1) % min(
            len(self.cached_image_list), IMAGES_TO_USE
        )
        self.update_image()

    def prior_image(self):
        """
        Moves to the previous image in the cached list. If at the beginning of the list,
        it loops back to the last image.
        """
        if self.image_number == 0:
            self.image_number = (
                min(len(self.cached_image_list), IMAGES_TO_USE) - 1
            )
        else:
            self.image_number -= 1
        self.update_image()

    def get_image_list(
        self,
        species_code: str,
        location: str,
        start_month: int,
        end_month: int,
    ) -> list:
        """Gets list of images urls."""
        if not self.cached_image_list:
            location_param = self._get_location_param(location)
            time_param = self._get_time_param(start_month, end_month)
            get_string = self._build_get_string(
                species_code, location_param, time_param
            )
            result = self._fetch_images(get_string)
            self.cached_image_list = self._extract_images(result.content)

        return self.cached_image_list

    def _get_location_param(self, location: str) -> str:
        """Returns the location parameter for the eBird API."""
        return f"&regionCode={location}" if location else ""

    def _get_time_param(self, start_month: int, end_month: int) -> str:
        """Returns the time parameter for the eBird API."""
        return (
            f"&beginMonth={start_month}&endMonth={end_month}"
            if start_month != 1 or end_month != 12
            else ""
        )

    def _build_get_string(
        self, species_code: str, location_param: str, time_param: str
    ) -> str:
        """Builds the URL for the eBird API request."""
        return (
            f"https://media.ebird.org/catalog?view=grid&taxonCode={species_code}"
            f"&sort=rating_rank_desc&mediaType=photo{location_param}{time_param}"
        )

    def _fetch_images(self, get_string: str) -> requests.Response:
        """Fetches images from the eBird API."""
        for retries in range(5):
            try:
                result = requests.get(get_string, timeout=20)
                result.raise_for_status()
                return result  # Exit loop if request is successful
            except requests.exceptions.RequestException as e:
                logging.warning(
                    "Get failed with %s, %d times", str(e), retries
                )
                if retries == 4:
                    sys.exit(1)  # Exit if all retries fail

    def _extract_images(self, content: str) -> list:
        """Extracts image URLs from the eBird API response."""
        content_str = str(content)
        images = re.findall(
            r"https://cdn\.download\.ams\.birds\.cornell\.edu/api/v\d/asset/\d+/1200",
            content_str,
        )
        # Filter and limit images based on requirements
        if len(images) > 2 + REQUIRED_IMAGES:
            return images[2::2][:IMAGES_TO_USE]
        return []

    def get_image(
        self,
        species_code: str,
        location: str,
        start_month: int,
        end_month: int,
    ) -> None:
        """Gets a requested image and displays it."""
        # e.g. display_image('comchi1', 'NO', 6 )
        image_list = self.get_image_list(
            species_code, location, start_month, end_month
        )

        # Try to get multiple images - otherwise expand search to other locations and times
        if len(image_list) <= REQUIRED_IMAGES:
            # Try looking at all locations
            logging.info(
                "Not enough images for %s at given location and time",
                species_code,
            )
            image_list = self.get_image_list(
                species_code, "", start_month, end_month
            )
            if len(image_list) <= REQUIRED_IMAGES:
                logging.info(
                    "Not enough images for %s at any location at given time",
                    species_code,
                )
                # Try looking at all times
                image_list = self.get_image_list(species_code, "", 1, 12)

        if len(image_list) > 0:
            try:
                result = requests.get(
                    image_list[self.image_number], timeout=10
                )
                result.raise_for_status()
                img_bytes = result.content
                image = Image.open(io.BytesIO(img_bytes))
            except requests.exceptions.RequestException as e:
                logging.warning("Get failed with %s", str(e))
                image = Image.open(
                    "photo_id/resources/Banner__Under_Construction__version_2.jpg"
                )
        else:
            logging.error(
                "No images for %s at any location or time", species_code
            )
            image = Image.open(
                "photo_id/resources/Banner__Under_Construction__version_2.jpg"
            )

        return image


class MatchWindow:
    """Class representing a match window which can be instantiated multiple times"""

    quiz_species = {}
    quiz_species_list = []

    def __init__(self, file: str, taxonomy: dict, have_list: list):
        self.root = Toplevel()
        quiz_data = process_quiz.process_quiz_file(file, taxonomy)
        species_list = quiz_data["species"]

        Label(
            self.root, text="Notes:" + quiz_data["notes"]
        ).pack()  # default value
        image_width = 420  # this is a good size for the images

        columns = self.root.winfo_screenwidth() // image_width

        rows = int(len(species_list) / columns) + 1

        # Create a photoimage object of the image in the path

        self.image_display = [
            [None for _ in range(columns)] for _ in range(rows + 1)
        ]
        self.frame = VerticalScrolledFrame(self.root)
        # self.frame.grid(row=1, column=0)
        self.frame.pack(fill="both", expand=1)

        self.root.title(self.root.title() + " :" + file)
        species_number = 0

        for row in range(1, rows + 1):
            for column in range(columns):
                logging.info(
                    "Processing image %d of %d",
                    species_number,
                    len(species_list),
                )
                if species_number >= len(species_list):
                    break
                self.image_display[row][column] = SpeciesFrame(
                    self.frame.interior,
                    species_number,
                    species_list,
                    quiz_data["location"],
                    quiz_data["start_month"],
                    quiz_data["end_month"],
                    image_width,
                )
                self.image_display[row][column].grid(row=row, column=column)
                species_number = species_number + 1

            if species_number >= len(species_list):
                break
        logging.info("Finished processing images")
        self.root.state("zoomed")
