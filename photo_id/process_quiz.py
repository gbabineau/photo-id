"""
    Processes a quiz file
"""

import json
import logging

def process_quiz_file(name : str, taxonomy : list) -> dict:
    """Reads a quiz file """

    result={}
    with open(name, encoding ='utf-8', mode= 'rt') as f:
        file_data = json.load(f)
    result['location']=file_data['location']
    result['start_month']=file_data['start_month']
    result['end_month']=file_data['end_month']
    result['species']=[]
    for species in file_data['species']:
        entry = next((item for item in taxonomy if item["comName"].upper() == species['name'].upper()), None)
        if entry == None:
            logging.info(f'Species not found {species["name"]}')
        else:
            result['species'].append(entry)
    result['species']=  sorted(result['species'], key=lambda x: x['taxonOrder'])
    return result


def get_code (data, common_name) -> str:
    """ Returns a species code for a common name """
    species = next((item for item in data['species'] if item["comName"] == common_name), None)
    return species['speciesCode']
