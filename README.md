# RO-Crate-Entry-Points

This repository contains a validation script for RO-Crates with entry points.
An entry point is a data entity of type `Dataset` that defines an `conformsTo` property pointing to an RO-Crate profile. 
The script validates that the entry point adheres to the specified profile, ensuring that the RO-Crate is structured correctly and meets the requirements of the profile.

If a specific profile is provided, the script will validate all entry points pointing to that profile.
If no profile is specified, the script will validate all entry points in the RO-Crate.

Additionally, the script checks if the input crate actually is a valid RO-Crate.

## Usage

To use the validation script, run the following command in your terminal:

```bash
python validate_entry_points.py <path_to_ro_crate_metadata_json> [--profile <profile_url>]
```

## Workflow

The script first finds all entry points through JSON-LD framing.
Then, each entry point is given as an unflattened JSON-LD object.
To allow for validation, the script transforms the entry point into the RO-Crate structure by flattening the JSON-LD graph, modifying the `@id` properties of all entities to be relative to the entry point, and adding the metadata entity of the RO-Crate.
Finally, the script validates the entry point using the `rocrate-validator` library.