"""
    Processes a quiz file
"""

import json
import logging

def process_quiz_file(name : str, taxonomy : list) -> dict:
    """Reads a quiz file """

    result={}
    with open(name, encoding ='utf-8', mode= 'rt') as file:
        file_data = json.load(file)
    result['location']=file_data['location']
    result['start_month']=file_data['start_month']
    result['end_month']=file_data['end_month']
    result['notes'] = '' if 'notes' not in file_data.keys() else file_data['notes']
    result['species']=[]
    for species in file_data['species']:
        entry = next((item for item in taxonomy if item["comName"].upper() == species['name'].upper()), None)
        if entry is None:
            logging.info(f'Species not found {species["name"]}')
        elif entry in result['species']:
            logging.info(f'Duplicate species removed {species["name"]}')
        else:
            entry['notes'] = '' if 'notes' not in species.keys() else species['notes']
            result['species'].append(entry)
    # Sort
    result['species']=  sorted(result['species'], key=lambda x: x['taxonOrder'])
    return result


def get_code (data, common_name) -> str:
    """ Returns a species code for a common name """
    species = next((item for item in data['species'] if item["comName"] == common_name), None)
    return species['speciesCode']
