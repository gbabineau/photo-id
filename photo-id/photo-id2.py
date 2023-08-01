import argparse
import io
import logging
import random
import re
import requests
#from tkinter import *
from tkinter import ttk, messagebox, Tk, Label, StringVar
from PIL import Image, ImageTk



class quiz_window:
    quiz_species = ''
    quiz_species_list=['none', 'comchi1', 'uraowl1', 'blueth']
    def __init__(self):
        self.quiz_species=str(random.choice(self.quiz_species_list))
        self.root = Tk()
        # Create a photoimage object of the image in the path
        test = ImageTk.PhotoImage(self.get_image('NO', 6))

        self.image_display = Label(image=test)
        self.image_display.image = test

        self.selected_species = StringVar(self.root)
        self.selected_species.set('') # default value
        ttk.OptionMenu(self.root, self.selected_species, *self.quiz_species_list, command=self.check_selection).grid()
        ttk.Button(self.root, text="New Image", command=self.update_image).grid()
        ttk.Button(self.root, text="New Species", command=self.update_species).grid()

        # Position image
        self.image_display.place(x=0, y=80)

        self.root.mainloop()

    def check_selection(self, args):
        if self.selected_species.get() == self.quiz_species:
            messagebox.showinfo(title='correct', message='Correct!')
            self.update_species()
        else:
            messagebox.showerror(title='incorrect', message='Try again!')

    def get_image(self, region_code : str,  month : int):
        # e.g. display_image('comchi1', 'NO', 6 )
        result=requests.get(f'https://media.ebird.org/catalog?view=grid&taxonCode={self.quiz_species}&sort=rating_rank_desc&mediaType=photo&regionCode={region_code}&beginMonth={month}&endMonth={month}')

        content = str(result.content)
        image_list =re.findall (r"https://cdn\.download\.ams\.birds\.cornell\.edu/api/v1/asset/\d+/1200", content)
        if len(image_list) > 2:
            image_number=random.randint(2,len(image_list)-1)
            img_bytes = requests.get(image_list[image_number]).content
            return Image.open(io.BytesIO(img_bytes))
        else:
            logging.error(f'No images for {self.quiz_species} at time and location')
            return Image.open('photo-id/resources/Banner__Under_Construction__version_2.jpg')

    def update_image(self):
        test2 = ImageTk.PhotoImage(self.get_image('NO', 6))
        self.image_display.configure(image=test2)
        self.image_display.image = test2

    def update_species(self):
        without_current_species=self.quiz_species_list.copy()
        without_current_species.remove(self.quiz_species)
        self.quiz_species=str(random.choice(without_current_species))
        self.update_image()

def main():
    arg_parser = argparse.ArgumentParser(
        description='Quiz on photo id.')
    arg_parser.add_argument(
        '--version', action='version', version='%(prog)s 0.0.0')
    arg_parser.add_argument(
        '--verbose', action='store_true', help='increase verbosity')


    args = arg_parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)


    quiz_window()


if __name__ == "__main__":
    main()
