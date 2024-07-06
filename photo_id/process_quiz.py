"""
    Processes a quiz file
"""

import json
import logging
import pathlib
import re


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
            entry['notes'] = species.get('notes', '')
            if 'frequency' in species:
                entry['frequency'] = species['frequency']
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


def get_code(data, common_name) -> str:
    """
    Retrieves the species code for a given common name from the provided data.

    Parameters:
    data (dict): The data containing species information.
    common_name (str): The common name of the species to find the code for.

    Returns:
    str: The species code if found, otherwise an empty string.
    """
    species = next(
        (item for item in data.get('species', []) if item["comName"].lower() == common_name.lower()), {})
    return species.get('speciesCode', '')


def get_notes(data, common_name) -> str:
    """
    Retrieves the notes for a given common name from the provided data.

    Parameters:
    data (dict): The data containing species information.
    common_name (str): The common name of the species to find notes for.

    Returns:
    str: The notes if found, otherwise an empty string.
    """
    species = next(
        (item for item in data.get('species', []) if item["comName"].lower() == common_name.lower()), {})
    return species.get('notes', '')


def get_frequency(data, common_name) -> str:
    """
    Retrieves the frequency for a given common name from the provided data.

    Parameters:
    data (dict): The data containing species information.
    common_name (str): The common name of the species to find the frequency for.

    Returns:
    int: The frequency if found, otherwise -1.
    """
    species = next(
        (item for item in data.get('species', []) if item["comName"].lower() == common_name.lower()), {})
    return species.get('frequency', -1)


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


def build_quiz_from_target_species(in_file: str, min_frequency: int, output_file: str, start_month: int, end_month: int, location_code: str) -> None:
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

    result = {"start_month": start_month,
              "end_month": end_month,
              "location": location_code,
              "species": []
              }
    line_number = 0
    with open(in_file, 'rt', encoding='utf-8') as target_file:
        end_of_file = False
        while not end_of_file:
            while not end_of_file:
                line = target_file.readline()
                line_number = line_number + 1
                if line == '':
                    end_of_file = True
                    break
                elif re.match("[0-9]+.", line) is not None:
                    break
            else:
                break
            if not end_of_file:
                species = target_file.readline()[:-1]
                line_number = line_number + 1
                while not end_of_file:
                    frequency_text = target_file.readline()[:-1]
                    line_number = line_number + 1
                    if frequency_text == '':
                        end_of_file = True  # should never go here.
                        logging.error(
                            "Incorrectly formatted file %s line %d", in_file, line_number)
                        break
                    elif re.match("[0-9]+.", frequency_text) is not None:
                        frequency = int(
                            re.match('[0-9]+', frequency_text).group(0))
                        if frequency < min_frequency:
                            end_of_file = True
                        break
                else:
                    break
                if not end_of_file:
                    result['species'].append({'comName': species, 'frequency': frequency,
                                              'notes': ''})

        with open(output_file, "wt", encoding='utf-8') as outfile:
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

