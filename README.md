# Species Conservation Status Tool

The Species Conservation tool created for this project uses data from the iNaturalist API to identify species with conservation concern in a specified geographic region. Given a location (such as a city, state, or country), this tool retrieves observations (species) from the iNaturalist API that are classified as threatened or vulnerable based on systems like NatureServe or the IUCN. The goal of the project is to make it easier to discover species of conservation interest that have been observed in a particular area using publicly available and citizen collected biodiversity data. Further info to come.

## Prerequisites
- Users must have Docker version 28.2.2 or later.
- Ensure this repository is cloned:
    - ```https://github.com/avallejo100/species-conservation-status-tool.git```

## Setup Instructions
Packages used:
- pyinaturalist
- redis

Libraries used:
- argparse
- logging
- socket
- json