from  ebird.api import get_taxonomy
import json
import logging
import os
import sys
ebird_api_key_name = 'EBIRDAPIKEY'


def process_quiz_file(name : str):
    result={}
    if not os.path.isfile('.cache/taxonomy'):
        ebird_api_key = os.getenv(ebird_api_key_name)
        if ebird_api_key == '0':
            sys.exit("ebird API key must be specified in the "+ebird_api_key_name+" environment variable.")
        taxonomy=get_taxonomy(ebird_api_key)
        with open('.cache/taxonomy', encoding ='utf-8', mode='wt') as f:
            json.dump(taxonomy, f)
    else:
        with open('.cache/taxonomy', encoding ='utf-8', mode= 'rt') as f:
            taxonomy=json.load(f)
    with open(name, encoding ='utf-8', mode= 'rt') as f:
        file_data = json.load(f)
    result['location']=file_data['location']
    result['start_month']=file_data['start_month']
    result['end_month']=file_data['end_month']
    result['species']=[]
    for species in file_data['species']:
        entry = next((item for item in taxonomy if item["comName"] == species['name']), None)
        if entry == None:
            logging.info(f'Species not found {species} name')
        else:
            result['species'].append(entry)
    result['species']=  sorted(result['species'], key=lambda x: x['taxonOrder'])
    return result


def get_code (data, common_name):
    species = next((item for item in data['species'] if item["comName"] == common_name), None)
    return species['speciesCode']

def main():
    quiz_data=process_quiz_file('tests/data/norway_common.json')

if __name__ == "__main__":
    main()
