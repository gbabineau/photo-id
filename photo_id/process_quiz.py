"""
    Processes a quiz file
"""

import json
import logging
import re

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


def build_quiz_from_target_species(in_file: str, min_frequency: int, output_file: str) -> None:
    """
        Accepts a target species url from eBird, sorted by frequency (descending)

        url : like https://ebird.org/targets?region=Oslo%2C+Norway+%28NO%29&r1=NO-03&bmo=5&emo=6&r2=NO-03&t2=day&mediaType=
        min_frequency : minimum frequency seen to be included in list
    """

    result =     {"start_month" : 5,
                "end_month" : 6,
                "location" : "NO",
                "species" : []
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
                        end_of_file = True # should never go here.
                        logging.error(
                            f"Incorrectly formatted file {in_file} line {line_number}")
                        break
                    elif re.match("[0-9]+.", frequency_text) is not None:
                        frequency = int(re.match('[0-9]+',frequency_text).group(0))
                        if frequency < min_frequency:
                            end_of_file = True
                        break
                else:
                    break
                if not end_of_file:
                    result['species'].append({'comName' : species, 'notes': f"frequency at location {frequency}"})

        with open(output_file, "wt", encoding='utf-8') as outfile:
            outfile.write(json.dumps(result, indent=2))


