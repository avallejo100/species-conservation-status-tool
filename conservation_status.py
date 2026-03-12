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
    '-p', '--place_id',
    type=str,
    required=False,
    default = 18,
    help='Place ID for iNaturalist API (default: 18)'
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
        r.set(key, json.dumps(observations))
        return observations

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
        taxa_list['statuses'] = o['taxon'].get('conservation_status')['status_name'] if o['taxon'].get('conservation_status') else None
        if taxa_list not in endangered_taxa:
            endangered_taxa.append(taxa_list)
    return endangered_taxa

# -------------------------
# MAIN
# -------------------------

if __name__ == "__main__":
    r = redis.Redis(host='127.0.0.1', port=6379, db=0)

    logging.info(f"Starting conservation status retrieval for place_id: {args.place_id}")
    observations = grab_observations(args.place_id)
    endangered_taxa = parse_observations(observations)
    logging.info(f"Retrieved endangered taxa information for place_id: {args.place_id}")

    print(json.dumps(endangered_taxa, indent=2))