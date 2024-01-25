"""
    Processes a quiz file
"""

import json
import logging


def sorted_species(initial_list: list, taxonomy: list) -> list:
    result = []
    for species in initial_list:
        entry = next((item for item in taxonomy if item["comName"].upper(
        ) == species['comName'].upper()), None)
        if entry is None:
            logging.info(f'Species not found {species["comName"]}')
        elif entry in result:
            logging.info(f'Duplicate species removed {species["comName"]}')
        else:
            entry['notes'] = '' if 'notes' not in species.keys(
            ) else species['notes']
            result.append(entry)
    # Sort
    result = sorted(result, key=lambda x: x['taxonOrder'])
    return result


def process_quiz_file(name: str, taxonomy: list) -> dict:
    """Reads a quiz file """

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
    """ Returns a species code for a common name """
    species = next(
        (item for item in data['species'] if item["comName"] == common_name), None)
    return species['speciesCode']


def sort_quiz(name: str, taxonomy: list) -> dict:
    """ Sorts a quiz taxonomically. This is not necessary to use an unsorted quiz file in the game
       because it is sorted dynamically. However, it can be a useful utility for breaking up a
       large quiz file into multiple shorter quizes and the breaklines can be taxonomic.
    """
    with open(name, encoding='utf-8', mode='rt') as file:
        result = json.load(file)

    result['species'] = sorted_species(result['species'], taxonomy)

    with open(name+'.sorted', encoding='utf-8', mode='wt') as file:
        json.dump(result, file, ensure_ascii=False, indent=4)
