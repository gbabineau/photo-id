"""
    Processes a quiz file
"""

import json
import logging
import pathlib
import re
import typing
import sys


def sorted_species(initial_list: list, taxonomy: list) -> list:
    """
    Sorts a list of species based on their taxonomic order.

    Parameters:
    initial_list: A list of dicts, each containing the common name of a species.
    taxonomy: A list of dicts, each containing the common name and taxonomic order of a species.

    Returns:
    list: A sorted list of species by their taxonomic order.
    """
    result = []
    for species in initial_list:
        entry = next((item for item in taxonomy if item["comName"].upper(
        ) == species['comName'].upper()), None)
        if entry is None:
            logging.info('Species not found %s', species["comName"])
        elif any(res["comName"].upper() == entry["comName"].upper() for res in result):
            logging.info('Duplicate species removed %s', species["comName"])
        else:
            entry = entry.copy()
            for key, value in species.items():
                if key not in entry.keys():
                    entry[key] = value
            result.append(entry)
    # Sort
    result = sorted(result, key=lambda x: x['taxonOrder'])
    return result


def process_quiz_file(name: str, taxonomy: list) -> dict:
    """
    Processes a quiz file and returns a dictionary with quiz details and sorted species.

    Parameters:
    name : The name of the quiz file to process.
    taxonomy : A list of dicts, each containing the common name and taxonomic order of a species.

    Returns:
    dict: A dictionary containing the quiz details including the sorted species.
    """
    result = {}
    with open(name, encoding='utf-8', mode='rt') as file:
        file_data = json.load(file)
    result['location'] = file_data['location']
    result['start_month'] = file_data['start_month']
    result['end_month'] = file_data['end_month']
    result['notes'] = '' if 'notes' not in file_data.keys() else file_data['notes']
    result['species'] = sorted_species(file_data['species'], taxonomy)
    return result


def sort_quiz(name: str, taxonomy: list) -> dict:
    """
    Sorts the species in a quiz file based on a given taxonomy and saves the result to a new file.

    Parameters:
    name (str): The name of the quiz file to process.
    taxonomy (list): A list of dictionaries, each containing the common name and taxonomic order of a species.
    """
    with open(name, encoding='utf-8', mode='rt') as file:
        result = json.load(file)

    result['species'] = sorted_species(result['species'], taxonomy)

    with open(name+'.sorted', encoding='utf-8', mode='wt') as file:
        json.dump(result, file, ensure_ascii=False, indent=4)


def build_quiz_from_target_species(
    in_file: str,
    min_frequency: int,
    output_file: str,
    start_month: int,
    end_month: int,
    location_code: str,
) -> None:
    """
    Accepts a target species url from eBird, sorted by frequency (descending)
    Get this from an url
    like https://ebird.org/targets?region=Oslo%2C+Norway+%28NO%29&r1=NO-03&bmo=5&emo=6&r2=NO-03&t2=day&mediaType=
    then cut and paste the list of species and frequencies into a text file.

    in_file : input file
    min_frequency : minimum frequency seen to be included in list
    output_file : output file
    start_month : starting month
    end_month : ending month
    location_code : 2 letter location code
    """

    def parse_line(line: str) -> bool:
        return re.match(r"\d+\.", line) is not None

    def parse_frequency(frequency_text: str) -> int:
        match = re.match(r"^\d+", frequency_text)
        if match:
            return int(match.group(0))
        return -1

    def read_species_and_frequency(file) ->typing.Dict[str, typing.Any]:
        species = file.readline().strip()
        while True:
            frequency_text = file.readline().strip()
            if not frequency_text:
                logging.error("Incorrectly formatted file %s", in_file)
                raise ValueError("Incorrectly formatted file")
            frequency = parse_frequency(frequency_text)
            if frequency >= 0:
                break
        return {"comName": species, "frequency": frequency, "notes": ""}

    result = {
        "start_month": start_month,
        "end_month": end_month,
        "location": location_code,
        "species": [],
    }

    with open(in_file, "rt", encoding="utf-8") as target_file:
        while True:
            line = target_file.readline()
            if not line:
                break
            if parse_line(line):
                try:
                    species_info = read_species_and_frequency(target_file)
                    if species_info["frequency"] >= min_frequency:
                        result["species"].append(species_info)
                except ValueError:
                    break

    with open(output_file, "wt", encoding="utf-8") as outfile:
        outfile.write(json.dumps(result, indent=2))


def split_quiz(in_file: str, max_size: int, taxonomy) -> None:
    """
    Splits a quiz file into multiple parts based on a maximum size.

    Parameters:
    in_file (str): The input file path of the quiz to be split.
    max_size (int): The maximum number of species per split quiz file.
    taxonomy (list): The taxonomy list used for sorting species.
    """
    quiz = process_quiz_file(name=in_file, taxonomy=taxonomy)
    length = len(quiz['species'])
    part = 1
    start = 0
    end = 0
    quiz['species'] = sorted_species(quiz['species'], taxonomy)
    while end < length:
        end = min(length, start + max_size)
        split = {key: value for key, value in quiz.items() if key != 'species'}
        split['species'] = quiz['species'][start:end]
        file_name = (
            f"{pathlib.Path(in_file).parent.resolve()}/"
            f"{pathlib.Path(in_file).stem}_Part{part}"
            f"{pathlib.Path(in_file).suffix}"
        )
        start = end
        with open(file_name, "wt", encoding='utf-8') as outfile:
            json.dump(split, outfile, indent=2)
        part += 1

def apply_avonet_data(filename, avonet_data):
    """
    Apply Avonet data to quizzes
    """
    try:
        with open(filename, encoding='utf-8', mode='rt') as file:
            quiz = json.load(file)
    except FileNotFoundError:
        logging.error("The file %s was not found.", filename)
        sys.exit(1)
    except IOError:
        logging.error("An I/O error occurred while reading the file %s.", filename)
        sys.exit(1)

    except json.JSONDecodeError:
        logging.error("The file %s contains invalid JSON.", filename)
        sys.exit(1)


    for species in quiz['species']:
        if 'sciName' not in species:
            logging.warning("The species %s does not have a scientific name.", species['comName'])
            continue
        species_name = species['sciName']
        avonet_info = avonet_data.get(species_name, {})
        species.update(avonet_info)

    try:
        with open(filename, encoding='utf-8', mode='wt') as file:
            json.dump(quiz, file, indent=2)
    except IOError:
        logging.error("An I/O error occurred while writing to the file %s", filename)
        sys.exit(1)
