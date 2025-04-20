"""
This module provides functionality to retrieve the eBird API key from an
environment variable.
Functions:
    get_ebird_api_key() -> str:
        Retrieves the eBird API key from the environment variable specified
        by `ebird_api_key_name`. If the API key is set to "0", the program
        terminates with an error message indicating that the API key must
Constants:
    ebird_api_key_name (str): The name of the environment variable that
    stores the eBird API key.
"""

import os
import sys

ebird_api_key_name = "EBIRDAPIKEY"


def get_ebird_api_key() -> str:
    """
    Retrieves the eBird API key from an environment variable.
    The function fetches the API key from the environment variable specified
    by the `ebird_api_key_name`. If the API key is set to "0", the program
    will terminate with an error message indicating that the API key must
    be specified.
    Returns:
        str: The eBird API key retrieved from the environment variable.
    Raises:
        SystemExit: If the API key is not properly specified.
    """
    ebird_api_key = os.getenv(ebird_api_key_name)
    if ebird_api_key == "0":
        sys.exit(
            "ebird API key must be specified in the "
            + ebird_api_key_name
            + " environment variable."
        )

    return ebird_api_key
