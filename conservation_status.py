#!/usr/bin/env python3
import pandas as pd # type: ignore

import os
import redis # type: ignore
import argparse
import logging
import socket
import json
import pyinaturalist as pin # type: ignore

# -------------------------
# Redis setup
# -------------------------
def get_redis():
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "redis-db"),
        port=6379,
        db=0,
        decode_responses=True
    )

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
    r = get_redis()

    key = f'observations_{place_id}'
    if r.exists(key):
        logging.debug("Observations already exist in Redis. Fetching from cache.")
        return json.loads(r.get(key))
    else:
        logging.debug("Fetching observations from iNaturalist API.")
        observations = pin.get_observations(
            place_id=place_id,
            per_page=500,
            csi=["EN", "CR", "VU"]
        )["results"]
        r.set(key, json.dumps(observations, default=str), ex=86400)
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
        return "Unknown"

    s = s.lower().strip()

    vulnerable = ["vulnerable", "vu", "g3", "s3", "vulnerable (vu)", "vulnerable (g3)", "vulnerable (s3)"]
    endangered = ["endangered", "en", "endangered (en)", "s2", "g2", "endangered (s2)", "endangered (g2)"]
    critically_endangered = ["critically endangered", "cr", "critically endangered (cr)", "s1", "g1", "critically endangered (s1)", "critically endangered (g1)"]
    imperiled = ["imperiled", "imperiled (g2)", "imperiled (s2)", "imp"]
    critically_imperiled = ["critically imperiled", "critically imperiled (g1)", "critically imperiled (s1)"]

    if s in vulnerable:
        return "Vulnerable"
    elif s in endangered:
        return "Endangered"
    elif s in critically_endangered:
        return "Critically Endangered"
    elif s in imperiled:
        return "Imperiled"
    elif s in critically_imperiled:
        return "Critically Imperiled"
    else:
        return "Other"

def parse_observations(obs: list) -> list:
    '''
    Parses a list of observations to extract taxa information and conservation statuses.
    Args:
        obs (list): A list of observations where each observation is a dictionary containing taxon information.
    Returns:
        list: A list of dictionaries, each containing the name, ID, and conservation status of a taxon.'''
    
    logging.debug(f"Parsing observations to extract taxa information.")

    endangered_taxa = []
    for o in obs:
        taxa_list = {}

        taxa_list['taxon_name'] = o['taxon']["iconic_taxon_name"] if o['taxon'].get("iconic_taxon_name") else None
        taxa_list['common_name'] = o['taxon']['preferred_common_name'] if o['taxon'].get('preferred_common_name') else None
        taxa_list['scientific_name'] = o['taxon']['name'] if o['taxon'].get('name') else None
        status = o['taxon'].get('conservation_status')['status_name'] if o['taxon'].get('conservation_status') else None
        taxa_list['statuses'] = normalize_status(status) if status else None
        taxa_list["photo_url"] = o['taxon']['default_photo']['medium_url'] if o['taxon'].get('default_photo') else None
        taxa_list["taxon_id"] = o["taxon"]["id"] if o['taxon'].get('id') else None
 
        if taxa_list not in endangered_taxa:
            endangered_taxa.append(taxa_list)
    
    logging.debug(f"Extracted taxa from observations.")

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
        logging.error(f"Place '{place_name}' not found")
        return []

    observations = grab_observations(place_id)

    endangered_taxa = parse_observations(observations)

    if not endangered_taxa:
        logging.error(f"No taxa found for place_id {place_id}")
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
