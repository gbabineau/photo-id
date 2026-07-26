import json
import logging
import os
import pathlib
import re
import sys
import datetime
from urllib.error import HTTPError
from xml.etree.ElementTree import ParseError as XMLParseError

from bs4 import BeautifulSoup
from selenium import webdriver


def get_species_from_hotspot_website(
    hotspot_name: str,
    hotspot_id: str,
    ebird_username: str,
    ebird_password: str,
    begin_month: int,
    end_month: int,
) -> list:
    logging.info(
        "Getting species from hotspot website: %s (%s)",
        hotspot_name,
        hotspot_id,
    )
    website = f"https://ebird.org/targets?r1={hotspot_id}&bmo={begin_month}&emo={end_month}&r2={hotspot_id}&t2=year&mediaType="
    website = website.replace(" ", "%20")
    species = []
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(300)
    try:
        driver.get(website)
        username = driver.find_element("id", "input-user-name")
        username.send_keys(ebird_username)
        password = driver.find_element("id", "input-password")
        password.send_keys(ebird_password)
        button = driver.find_element("id", "form-submit")

        # Click the button
        button.click()

        soup = BeautifulSoup(driver.page_source, "html.parser")
        species_list = soup.find_all(
            "li",
            class_="ResultsStats ResultsStats--action ResultsStats--toEdge",
        )  # Replace with actual class name
        if len(species_list) == 0:
            logging.error(
                "No species found for hotspot '%s' with ID '%s'. Will retry.",
                hotspot_name,
                hotspot_id,
            )
            driver.save_screenshot("no_species_found.png")
            return []

        for species_item in species_list:
            species_name = species_item.find("div", "ResultsStats-title").text
            species_name = species_name.split("Exotic")[0].strip()
            species_name = species_name.strip()
            species_frequency = species_item.find(
                "div", "ResultsStats-stats"
            ).text
            species_frequency = species_frequency.strip()
            species_frequency = float(species_frequency.split("%")[0].strip())
            species.append(
                {"comName": species_name, "frequency": species_frequency}
            )
    except (HTTPError, AttributeError, XMLParseError) as e:
        logging.exception(
            "Error parsing website for hotspot '%s': %s", hotspot_name, str(e)
        )
    finally:
        driver.quit()

    logging.info(
        "Found %d species for hotspot '%s' with ID '%s'.",
        len(species),
        hotspot_name,
        hotspot_id,
    )
    return species


def get_cached_species_from_hotspot_website(
    cache_directory: str,
    hotspot_name: str,
    hotspot_id: str,
    ebird_username: str,
    ebird_password: str,
    begin_month: int,
    end_month: int,
) -> list:
    """Retrieves species data from a cached file or fetches it from the eBird website."""
    cache_subdirectory = os.path.join(cache_directory, "hotspots")
    if not os.path.exists(cache_subdirectory):
        os.makedirs(cache_subdirectory, exist_ok=True)

    hotspot_id_matches = re.findall(r"L\d+", hotspot_id)
    if hotspot_id_matches:
        hotspot_id = hotspot_id_matches[-1]

    cache_name = f"{os.path.join(cache_subdirectory, hotspot_id)}.json"
    if not os.path.exists(cache_name):
        attempts = 0
        species = []
        while attempts < 3 and not species:
            species = get_species_from_hotspot_website(
                hotspot_name,
                hotspot_id,
                ebird_username,
                ebird_password,
                begin_month=begin_month,
                end_month=end_month,
            )
            attempts += 1
        if attempts > 3:
            logging.error(
                "Failed to retrieve species for hotspot '%s' after 3 attempts.",
                hotspot_name,
            )
            sys.exit(1)
        if len(species) > 0:
            with open(cache_name, "wt", encoding="utf-8") as file:
                json.dump(species, file)
    else:
        with open(cache_name, "rt", encoding="utf-8") as file:
            species = json.load(file)
    return species


def process_trip(trip_file: str) -> dict:
    """
    Processes a trip file and returns a dictionary with trip details and sorted species.

    Parameters:
    trip_file : The name of the trip file to process."
    taxonomy : A list of dicts, each containing the common name and taxonomic order of a species."
    """
    try:
        with open(trip_file, "rt", encoding="utf-8") as file:
            trip_data = json.load(file)
    except FileNotFoundError:
        logging.error("The file '%s' was not found.", trip_file)
        sys.exit(1)
    except json.JSONDecodeError:
        logging.error("Error decoding JSON from the file '%s'.", trip_file)
        sys.exit(1)

    # Check if the trip data is in the expected format
    if not isinstance(trip_data, dict) or "itinerary" not in trip_data:
        logging.error("Invalid trip data format in '%s'.", trip_file)
        sys.exit(1)
    return trip_data


def get_file_modification_time(file_path: pathlib.Path) -> str:
    """Return the file modification time for the given path."""
    try:
        mtime = file_path.stat().st_mtime
        return datetime.datetime.fromtimestamp(mtime).isoformat(
            sep=" ", timespec="seconds"
        )
    except (OSError, FileNotFoundError) as e:
        logging.warning(
            "Unable to get modification time for %s: %s", file_path, str(e)
        )
        return ""


def update_species_frequency(
    species: dict, trip_data: dict, hotspot_species: list
) -> None:
    if species["frequency"] >= trip_data["minimum_frequency"]:
        if species["comName"] not in [s["comName"] for s in hotspot_species]:
            hotspot_species.append(
                {
                    "comName": species["comName"],
                    "frequency": [species["frequency"]],
                }
            )
        else:
            for existing_species in hotspot_species:
                if existing_species["comName"] == species["comName"]:
                    existing_species["frequency"].append(species["frequency"])
                    break


def get_hotspot_species(
    hotspots, trip_data, cache_directory, ebird_username, ebird_password
) -> list:
    hotspot_species = []
    for hotspot in hotspots:
        species_list = get_cached_species_from_hotspot_website(
            cache_directory,
            hotspot["name"],
            hotspot["hotspotId"],
            ebird_username,
            ebird_password,
            begin_month=trip_data["start_month"],
            end_month=trip_data["end_month"],
        )
        for species in species_list:
            update_species_frequency(
                species=species,
                trip_data=trip_data,
                hotspot_species=hotspot_species,
            )

    # Average the frequencies for each species
    for species_in_day in hotspot_species:
        species_in_day["frequency"] = round(
            sum(species_in_day["frequency"]) / len(species_in_day["frequency"]),
            2,
        )
    return hotspot_species


HOTSPOT_SPECIES_KEY = "hotspot species"


def get_ebird_data(
    trip_data: dict,
    ebird_username: str,
    ebird_password: str,
    cache_directory: str,
) -> dict:
    result = {
        "name": trip_data["name"],
        "location": trip_data["location"],
        "description": trip_data["description"],
        "website": trip_data["website"],
        "date": trip_data["date"],
        "start_month": trip_data["start_month"],
        "end_month": trip_data["end_month"],
        "minimum_frequency": trip_data.get("minimum_frequency", 0.0),
    }
    # Process the trip data to get the species
    days = []
    itinerary = trip_data["itinerary"]
    for day in itinerary:
        day[HOTSPOT_SPECIES_KEY] = get_hotspot_species(
            day.get("hotspots", []),
            trip_data,
            cache_directory,
            ebird_username,
            ebird_password,
        )

        days.append(day)
    result["itinerary"] = days

    return result


def updates_species_with_taxonomy(species: dict, taxonomy: list) -> None:
    for taxon in taxonomy:
        if species["comName"] == taxon["comName"]:
            for key in taxon.keys():
                if key not in species:
                    species[key] = taxon[key]
            break


def update_species_with_information_mentioned_in_trip(
    hotspot_species_list: list, species: str
) -> None:
    found = False
    for hotspot_species in hotspot_species_list:
        if species == hotspot_species["comName"]:
            hotspot_species["notes"] = "Mentioned in trip data"
            found = True
            break
    if not found:
        hotspot_species_list.append(
            {"comName": species, "notes": "Mentioned in trip data"}
        )


def add_taxonomy(with_ebird_species_data: list, taxonomy: list) -> list:
    """Add taxonomy data to the species in the trip data.
    Args:
        with_ebird_species_data (list): The trip data with eBird species data.
        taxonomy (list): The taxonomy data to add.
    Returns:
        list: The trip data with added taxonomy data.
    """
    for day in with_ebird_species_data:
        for species in day[HOTSPOT_SPECIES_KEY]:
            updates_species_with_taxonomy(species, taxonomy)
    return with_ebird_species_data


def add_mentions(trip_data: list, taxonomy: list) -> list:
    for day in trip_data:
        for species in day.get("mentioned", []):
            taxon_entry = next(
                (taxon for taxon in taxonomy if taxon["comName"] == species),
                None,
            )
            if not taxon_entry:
                logging.warning(
                    "Taxon entry for '%s' not found in taxonomy.", species
                )
            else:
                update_species_with_information_mentioned_in_trip(
                    hotspot_species_list=day[HOTSPOT_SPECIES_KEY],
                    species=species,
                )

    return trip_data


def keep_high_frequency(trip_data: list, frequency: float) -> list:
    for day in trip_data:
        day[HOTSPOT_SPECIES_KEY] = [
            species
            for species in day[HOTSPOT_SPECIES_KEY]
            if species.get("frequency", 100.0) / 100 >= frequency
        ]
    return trip_data


def sort_species_by_taxonomy(trip_data: list) -> list:
    for day in trip_data:
        day[HOTSPOT_SPECIES_KEY] = sorted(
            day[HOTSPOT_SPECIES_KEY], key=lambda x: x.get("taxonOrder", 0)
        )
    return trip_data


def split_trip(trip_data: dict) -> list:
    quizzes = []
    trip_location = trip_data.get("location", None)
    trip_start_month = trip_data.get("start_month", 1)
    trip_end_month = trip_data.get("end_month", 12)
    for day in trip_data["itinerary"]:
        quiz = {
            "start_month": trip_start_month
            if trip_start_month
            else day.get("start_month", 1),
            "end_month": trip_end_month
            if trip_end_month
            else day.get("end_month", 12),
            "location": trip_location
            if trip_location
            else day.get("location", None),
            "basis": "Trip data automatically generated from trip file",
            "species": day[HOTSPOT_SPECIES_KEY],
            "day": day.get("day", 1),
        }
        if day.get("AM_title"):
            quiz["notes"] = (
                f"Morning: {day['AM_title']}. Afternoon: {day.get('PM_title', '')}"
            )
        else:
            quiz["notes"] = f"Full: {day.get('Full day title', '')}."
        quizzes.append(quiz)

    return quizzes


def write_quiz_to_file(quiz: dict, output_file: str) -> None:
    """Write the quiz data to a JSON file."""
    with open(output_file, "wt", encoding="utf-8") as file:
        json.dump(quiz, file, indent=4)
    print(f"Quiz data written to {output_file}")


def _get_species_to_remove(
    species, next_day_species, to_remove_from_day, to_remove_from_next_day
):
    """Helper function to determine which species to remove from day to day
    based on frequency."""
    for next_species in next_day_species:
        if species["comName"] == next_species["comName"]:
            # if it is mentioned on the first day, remove it from the next day
            if species.get("notes"):
                to_remove_from_next_day.append(next_species)
            elif next_species.get("notes"):
                # if it is mentioned on the next day, remove it from the first day
                to_remove_from_day.append(species)
            # otherwise if the first one has a higher or equal frequency, remove the next one
            elif species.get("frequency", 0) >= next_species.get(
                "frequency", 0
            ):
                to_remove_from_next_day.append(next_species)
            else:
                to_remove_from_day.append(species)
            break


def _find_and_remove_shared_species(day, next_day):
    """Helper function to remove shared species between two days."""
    to_remove_from_next_day = []
    to_remove_from_day = []

    for species in day[HOTSPOT_SPECIES_KEY]:
        _get_species_to_remove(
            species,
            next_day[HOTSPOT_SPECIES_KEY],
            to_remove_from_day,
            to_remove_from_next_day,
        )

    for species in to_remove_from_next_day:
        next_day[HOTSPOT_SPECIES_KEY].remove(species)
    for species in to_remove_from_day:
        if species in day[HOTSPOT_SPECIES_KEY]:
            day[HOTSPOT_SPECIES_KEY].remove(species)


def remove_species_shared_in_common(trip_data: list) -> list:
    """Remove species that are shared in common between days, keeping only the occurrence with the highest probability."""

    for i, day in enumerate(trip_data):
        for j in range(i + 1, len(trip_data)):
            _find_and_remove_shared_species(day, trip_data[j])

    return trip_data


cache_valid = True


class Cache:
    """A class to manage caching of trip data."""

    def __init__(self, directory, title, trip_update_time, starting_valid=True):
        self.cache_valid = starting_valid
        self.cache_directory = directory
        self.trip_title = title
        self.trip_update_time = trip_update_time

    def available(self, cache_type) -> dict:
        """
        Check if the cache file is available and not dated and return its
        content if so.
        """
        cache_path = pathlib.Path(
            os.path.join(
                self.cache_directory, f"{self.trip_title}_{cache_type}.json"
            )
        )
        if cache_valid and cache_path.exists():
            cache_update_time = get_file_modification_time(cache_path)
            if cache_update_time < self.trip_update_time:
                logging.info(
                    "Not using cache for %s %s as it is older than the trip data.",
                    self.trip_title,
                    cache_type,
                )
                cache_path.unlink(missing_ok=True)
                return {}

            else:
                logging.info(
                    "Using cache for %s %s", self.trip_title, cache_type
                )
                with cache_path.open("rt", encoding="utf-8") as input_file:
                    return json.load(input_file)
        return {}

    def update(self, cache_type, data) -> None:
        """
        Update the cache file with the given data.
        """
        os.makedirs(self.cache_directory, exist_ok=True)
        cache_file = os.path.join(
            self.cache_directory, f"{self.trip_title}_{cache_type}.json"
        )
        with open(cache_file, "wt", encoding="utf-8") as output_file:
            json.dump(data, output_file, indent=4)
        self.cache_valid = False


def create_quizes_from_trip_data(
    trip_file: pathlib.Path, username: str, password: str, taxonomy: list
) -> None:
    """Create quizzes from trip data by processing the trip file and generating
    quizzes for each day."""
    trip_title = trip_file.stem
    trip_directory = trip_file.parent.resolve()
    cache_directory = ".cache"
    file_update_time = get_file_modification_time(trip_file)
    logging.info(
        "Trip file '%s' last updated: %s",
        trip_file,
        file_update_time,
    )
    trip_last_update_time = get_file_modification_time(trip_file)
    trip_cache = Cache(cache_directory, trip_title, trip_last_update_time)
    if (trip_data := trip_cache.available("ITINERARY")) == {}:
        trip_data = process_trip(
            str(trip_file.resolve()),
        )

        trip_cache.update("ITINERARY", trip_data)

    if (new_data := trip_cache.available("EBIRD")) == {}:
        trip_data = get_ebird_data(
            trip_data,
            username,
            password,
            cache_directory=cache_directory,
        )
        trip_cache.update("EBIRD", trip_data)
    else:
        trip_data = new_data

    trip_data["itinerary"] = add_mentions(trip_data["itinerary"], taxonomy)

    if (new_data := trip_cache.available("TAXONOMY")) == {}:
        trip_data["itinerary"] = add_taxonomy(trip_data["itinerary"], taxonomy)

        trip_cache.update("TAXONOMY", trip_data)
    else:
        trip_data = new_data

    trip_data["itinerary"] = keep_high_frequency(trip_data["itinerary"], 0.01)

    trip_data["itinerary"] = sort_species_by_taxonomy(trip_data["itinerary"])

    trip_data["itinerary"] = remove_species_shared_in_common(
        trip_data["itinerary"]
    )

    # break this into quizzes by day
    quizzes = split_trip(trip_data)
    os.makedirs(f"{trip_directory}/generated_quizzes", exist_ok=True)
    for quiz in quizzes:
        output_file = f"{trip_directory}/generated_quizzes/Day {quiz['day']} with {len(quiz['species'])} species.json"
        write_quiz_to_file(quiz, output_file)
