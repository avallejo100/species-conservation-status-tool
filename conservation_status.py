#!/usr/bin/env python3
import redis # type: ignore
import pyinaturalist as pin # type: ignore

obs = pin.get_observations(
    place_id=18,
    per_page=200,
    csi=["EN", "CR", "VU"]
)["results"]

endangered_taxa = []

for o in obs:
    taxa_list = {}
    taxa_list['name'] = o['taxon']['name']
    taxa_list['id'] = o['taxon']['id']
    taxa_list['statuses'] = o['taxon'].get('conservation_status')['status_name'] if o['taxon'].get('conservation_status') else None
    if taxa_list not in endangered_taxa:
        endangered_taxa.append(taxa_list)

for t in endangered_taxa:
    print(t['name'], " | ", t['statuses'])

