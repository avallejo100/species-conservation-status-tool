#!/usr/bin/env python3
import pandas as pd # type: ignore

import redis # type: ignore
import argparse
import logging
import socket
import json
import pyinaturalist as pin # type: ignore

# -------------------------
# Redis setup
# -------------------------
r = redis.Redis(host='127.0.0.1', port=6379, db=0, decode_responses=True)

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
    Fetches observations from iNaturalist API for a given place_id, checking Redis cache first to avoid redundant API calls.
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

    s = s.lower().strip()

    mapping = {
    "vu": "Vulnerable",
    "vulnerable": "Vulnerable",
    "vulnerable (g3)": "Vulnerable",

    "en": "Endangered",
    "endangered": "Endangered",

    "cr": "Critically Endangered",
    "critically endangered": "Critically Endangered",

    "s2": "Imperiled",
    "imperiled": "Imperiled",

    "s1": "Critically Imperiled",
    "critically imperiled": "Critically Imperiled"
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
    return endangered_taxa # store this in redis for caching instead

def get_species_info(place_name: str) -> list:
    '''
    Retrieves species information for a given place ID and name, utilizing Redis for caching.
    Args:
        place_id (int): The ID of the place to fetch species information for.
        place_name (str): The name of the place to include in the output.
    Returns:
        tuple: A tuple containing a message, a Plotly figure, a list of species records, and column definitions.'''
    place_name_clean = place_name.strip().lower()
    place_id = grab_place_id(place_name_clean)

    if place_id is None:
        logging.error(f"Place name '{place_name}' not found in iNaturalist API.")
        return []
    
    key = f'observations_{place_id}'

    if not r.exists(key):
        logging.debug(f"No cached data for place_id {place_id}. Fetching from iNaturalist API.")
        observations = grab_observations(place_id)
        endangered_taxa = parse_observations(observations)
        
        r.set(key, json.dumps(endangered_taxa, default=str))
    else:
        logging.debug(f"Cached data found for place_id {place_id}. Fetching from Redis.")
        endangered_taxa = json.loads(r.get(key))
    
    if not endangered_taxa:
        logging.error(f"No endangered species data found for place_id {place_id}.")
        return []
    return endangered_taxa


# -------------------------
# MAIN
# -------------------------

if __name__ == "__main__":
    try:
        logging.info(f"Fetching species information for place: {args.place_name}")
        endangered_taxa = get_species_info(args.place_name)
    except Exception as e:
        logging.error(f"An error occurred while fetching species information: {e}")
        endangered_taxa = []

    print(json.dumps(endangered_taxa, indent=2))
