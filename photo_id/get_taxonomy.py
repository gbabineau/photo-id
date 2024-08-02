from ebird.api import get_taxonomy
import json
import os
import sys
ebird_api_key_name = 'EBIRDAPIKEY'


def ebird_taxonomy() -> list:
    """
    Retrieves the ebird taxonomy.

    Returns:
        list: The ebird taxonomy.
    """
    taxonomy = []
    cache_file = '.cache/taxonomy'
    if not os.path.isfile(cache_file):
        ebird_api_key = os.getenv(ebird_api_key_name)
        if ebird_api_key == '0':
            sys.exit("ebird API key must be specified in the " +
                     ebird_api_key_name+" environment variable.")
        taxonomy = get_taxonomy(ebird_api_key)
        with open(cache_file, encoding='utf-8', mode='wt') as f:
            json.dump(taxonomy, f)
    else:
        with open(cache_file, encoding='utf-8', mode='rt') as f:
            taxonomy = json.load(f)
    return taxonomy
