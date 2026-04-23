#!/usr/bin/env python3
import redis # type: ignore
import argparse
import logging
import socket
import json
import pyinaturalist as pin # type: ignore

# -------------------------
# Logging setup
# -------------------------

parser = argparse.ArgumentParser(description='Summarize FASTA file and output TXT summary')
parser.add_argument(
    '-l', '--loglevel',
    required=False,
    choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
    default='WARNING',
    help='Set the logging level (default: WARNING)'
)
parser.add_argument(
    '-p', '--place_name',
    type=str,
    required=False,
    default = 'Texas',
    help='Place name for iNaturalist API (default: Texas)'
)
args = parser.parse_args()

format_string = (
    f'[%(asctime)s {socket.gethostname()}] '
    '%(module)s.%(funcName)s:%(lineno)s - %(levelname)s - %(message)s'
)
logging.basicConfig(level=args.loglevel, format=format_string)

# -------------------------
# FUNCTIONS
# -------------------------

def grab_place_id(name: str) -> int | None:
    '''
    Grabs the place ID from iNaturalist API for a given place name.
    Args:
        name (str): The name of the place to fetch the ID for.
    Returns:
        int: The ID of the place.
    '''
    response = pin.get_places_autocomplete(name)
    return response["results"][0]["id"] if response["results"] else None

def grab_observations(place_id: int) -> list:
    '''
    Fetches observations from iNaturalist API for a given place_id, and saves results to Redis.
    Args:
        place_id (int): The ID of the place to fetch observations for.
    Returns:
        list: A list of observations fetched from the iNaturalist API or Redis database.'''

    key = f'observations_{place_id}'

    if r.exists(key):
        logging.debug("Observations already exist in Redis. Fetching from cache.")
        return json.loads(r.get(key))
    else:
        logging.debug("Fetching observations from iNaturalist API.")
        observations = pin.get_observations(
            place_id=place_id,
            per_page=200,
            csi=["EN", "CR", "VU"]
        )["results"]
        r.set(key, json.dumps(observations, default=str))
        return observations

def normalize_status(s: str | None) -> str | None:
    """
    Normalizes conservation status strings to a standard format.
    Args:
        s (string or None): The conservation status string to normalize.
    Returns:
        str or None: The normalized conservation status string.
    """
    if not s:
        return None

    s = s.lower()

    mapping = {
        "vu": "Vulnerable",
        "vulnerable": "Vulnerable",
        "en": "Endangered",
        "endangered": "Endangered",
        "cr": "Critically Endangered",
        "critically endangered": "Critically Endangered",
    }

    return mapping.get(s, s.title())

def parse_observations(obs: list) -> list:
    '''
    Parses a list of observations to extract taxa information and conservation statuses.
    Args:
        obs (list): A list of observations where each observation is a dictionary containing taxon information.
    Returns:
        list: A list of dictionaries, each containing the name, ID, and conservation status of a taxon.'''

    endangered_taxa = []
    for o in obs:
        taxa_list = {}
        taxa_list['name'] = o['taxon']['name']
        taxa_list['id'] = o['taxon']['id']
        status = o['taxon'].get('conservation_status')['status_name'] if o['taxon'].get('conservation_status') else None
        taxa_list['statuses'] = normalize_status(status) if status else None
        if taxa_list not in endangered_taxa:
            endangered_taxa.append(taxa_list)
    return endangered_taxa

# -------------------------
# MAIN
# -------------------------

if __name__ == "__main__":
    r = redis.Redis(host='127.0.0.1', port=6379, db=0)

    place_id = grab_place_id(args.place_name)
    logging.info(f"Starting conservation status retrieval for place_id: {place_id}")
    
    try:
        if place_id is None:
            raise ValueError(f"Place name '{args.place_name}' not found in iNaturalist API.")
    except ValueError as e:
        logging.error(e)
        exit(1)

    observations = grab_observations(place_id)
    endangered_taxa = parse_observations(observations)
    logging.info(f"Retrieved endangered taxa information for place_id: {place_id}")
    print(json.dumps(endangered_taxa, indent=2))