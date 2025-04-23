import json
import logging
import os
import sys
from urllib.error import HTTPError
from xml.etree.ElementTree import ParseError as XMLParseError
from selenium import webdriver
from bs4 import BeautifulSoup


def get_species_from_hotspot_website(
    hotspot_name: str,
    hotspot_id: str,
    ebird_username: str,
    ebird_password: str,
) -> list:
    logging.info(
        "Getting species from hotspot website: %s (%s)",
        hotspot_name,
        hotspot_id,
    )
    website = f"https://ebird.org/targets?r1={hotspot_id}&bmo=2&emo=2&r2=L604642&t2=year&mediaType="
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
                "No species found for hotspot '%s' with ID '%s'.",
                hotspot_name,
                hotspot_id,
            )
            driver.save_screenshot("no_species_found.png")
            sys.exit(1)

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
        logging.error(
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
) -> list:
    cache_subdirectory = os.path.join(cache_directory, "hotspots")
    if not os.path.exists(cache_subdirectory):
        os.makedirs(cache_subdirectory, exist_ok=True)
    cache_name = f"{os.path.join(cache_subdirectory, hotspot_id)}.json"
    if not os.path.exists(cache_name):
        species = get_species_from_hotspot_website(
            hotspot_name, hotspot_id, ebird_username, ebird_password
        )
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
    }
    # Process the trip data to get the species
    days = []
    itinerary = trip_data["itinerary"]
    for day in itinerary:
        day["hotspot species"] = []
        for hotspot in day.get("hotspots", []):
            species_list = get_cached_species_from_hotspot_website(
                cache_directory,
                hotspot["name"],
                hotspot["hotspotId"],
                ebird_username,
                ebird_password,
            )
            for species in species_list:
                if species["comName"] not in [
                    s["comName"] for s in day["hotspot species"]
                ]:
                    day["hotspot species"].append(
                        {
                            "comName": species["comName"],
                            "frequency": [species["frequency"]],
                        }
                    )
                else:
                    for existing_species in day["hotspot species"]:
                        if existing_species["comName"] == species["comName"]:
                            existing_species["frequency"].append(
                                species["frequency"]
                            )
                            break
        # Average the frequencies for each species
        for species_in_day in day["hotspot species"]:
            species_in_day["frequency"] = sum(
                species_in_day["frequency"]
            ) / len(species_in_day["frequency"])

        days.append(day)
    result["itinerary"] = days

    return result


def add_taxonomy(with_ebird_species_data: list, taxonomy: list) -> list:
    """Add taxonomy data to the species in the trip data.
    Args:
        with_ebird_species_data (list): The trip data with eBird species data.
        taxonomy (list): The taxonomy data to add.
    Returns:
        list: The trip data with added taxonomy data.
    """
    for day in with_ebird_species_data:
        for species in day["hotspot species"]:
            for taxon in taxonomy:
                if species["comName"] == taxon["comName"]:
                    for key in taxon.keys():
                        if key not in species.keys():
                            species[key] = taxon[key]
                    break
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
                found = False
                for hotspot_species in day["hotspot species"]:
                    if species == hotspot_species["comName"]:
                        hotspot_species["notes"] = "Mentioned in trip data"
                        found = True
                        break
                if not found:
                    day["hotspot species"].append(
                        {"comName": species, "notes": "Mentioned in trip data"}
                    )
    return trip_data


def keep_high_frequency(trip_data: list, frequency: float) -> list:
    for day in trip_data:
        day["hotspot species"] = [
            species
            for species in day["hotspot species"]
            if species.get("frequency", 100.0) / 100 >= frequency
        ]
    return trip_data


def sort_species_by_taxonomy(trip_data: list) -> list:
    for day in trip_data:
        day["hotspot species"] = sorted(
            day["hotspot species"], key=lambda x: x.get("taxonOrder", 0)
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
            "species": day["hotspot species"],
            "day": day.get("day", 1),
        }
        if day.get("AM_title"):
            quiz["title"] = (
                f"Morning: {day['AM_title']}. Afternoon: {day.get('PM_title', '')}"
            )
        else:
            quiz["title"] = f"Full: {day.get('Full day title', '')}."
        quizzes.append(quiz)

    return quizzes


def write_quiz_to_file(quiz: dict, output_file: str) -> None:
    with open(output_file, "wt", encoding="utf-8") as file:
        json.dump(quiz, file, indent=4)
    print(f"Quiz data written to {output_file}")


def _find_and_remove_shared_species(day, next_day):
    """Helper function to remove shared species between two days."""
    to_remove_from_next_day = []
    to_remove_from_day = []

    for species in day["hotspot species"]:
        com_name = species["comName"]
        for next_species in next_day["hotspot species"]:
            if com_name == next_species["comName"]:
                # if it is mentioned on the first day, remove it from the next day
                if species.get("notes"):
                    to_remove_from_next_day.append(next_species)
                elif next_species.get("notes"):
                    # if it is mentioned on the next day, remove it from the first day
                    to_remove_from_day.append(species)
                # otherwise if the first one has a higher or equal frequency, remove the next one
                # else remove the first one
                elif species.get("frequency", 0) >= next_species.get(
                    "frequency", 0
                ):
                    to_remove_from_next_day.append(next_species)
                else:
                    to_remove_from_day.append(species)
                break

    for species in to_remove_from_next_day:
        next_day["hotspot species"].remove(species)
    for species in to_remove_from_day:
        if species in day["hotspot species"]:
            day["hotspot species"].remove(species)


def remove_species_shared_in_common(trip_data: list) -> list:
    """Remove species that are shared in common between days, keeping only the occurrence with the highest probability."""

    for i, day in enumerate(trip_data):
        for j in range(i + 1, len(trip_data)):
            _find_and_remove_shared_species(day, trip_data[j])

    return trip_data
