# RO-Crate-Entry-Points

This repository contains a validation script for RO-Crates with entry points.
An entry point is a data entity of type `Dataset` that defines an `conformsTo` property pointing to an RO-Crate profile. 
The script validates that the entry point adheres to the specified profile, ensuring that the RO-Crate is structured correctly and meets the requirements of the profile.
If a specific profile is provided, the script will validate all entry points pointing to that profile.
If no profile is specified, the script will validate all entry points in the RO-Crate.

## Usage

To use the validation script, run the following command in your terminal:

```bash
python validate_entry_points.py <path_to_ro_crate_metadata_json> [--profile <profile_url>]
``` 