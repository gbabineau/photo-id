from ebird.api import get_taxonomy
import json
import os
import sys
ebird_api_key_name = 'EBIRDAPIKEY'


def ebird_taxonomy() -> list:
    " returns the current eBird taxonomy or a cached version "
    taxonomy = []
    if not os.path.isfile('.cache/taxonomy'):
        ebird_api_key = os.getenv(ebird_api_key_name)
        if ebird_api_key == '0':
            sys.exit("ebird API key must be specified in the " +
                     ebird_api_key_name+" environment variable.")
        taxonomy = get_taxonomy(ebird_api_key)
        with open('.cache/taxonomy', encoding='utf-8', mode='wt') as f:
            json.dump(taxonomy, f)
    else:
        with open('.cache/taxonomy', encoding='utf-8', mode='rt') as f:
            taxonomy = json.load(f)
    return taxonomy
