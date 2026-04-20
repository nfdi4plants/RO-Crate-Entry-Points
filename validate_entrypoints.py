from pyld import jsonld
import json
import argparse
from rocrate_validator.services import validate_metadata_as_dict
from rocrate_validator.models import Profile
from rocrate_validator.services import get_profiles

# This script is a test for using pyld to extract entry points from a RO-Crate and validate them against an RO-Crate profile

# ========================================================================
# command line arguments: input file, profile ID to filter entry points on
parser = argparse.ArgumentParser(description="extract entry points from a RO-Crate and create sub-RO-Crates for each entry point")
parser.add_argument("input", help="Input RO-Crate metadata file")
parser.add_argument("-p", "--profile", help="Profile ID to filter entry points on")
args = parser.parse_args()

input = args.input

profileID = args.profile

# if not profileID:
#     print("No profile ID provided, exiting")
#     exit(1)

# ========================================================================
# define some constants and helper functions for processing the RO-Crate metadata

# required top-level metadata for any RO-Crate
default_metadata_obj = {
    "@id": "ro-crate-metadata.json",
    "@type": "CreativeWork",
    "conformsTo": {
        "@id": "https://w3id.org/ro/crate/1.1"
    },
    "about": {
        "@id": "./"
    }
}

# frame for extracting entry points (datasets that specify conformsTo)
frame = {
  "@context": "https://w3id.org/ro/crate/1.2/context",
  "@type": "Dataset",
  "conformsTo": {
    "@type": ["CreativeWork", "Profile"], # (not working unfortunately)
    "@requireAll": True
  },
  "@requireAll": True
}

# options for pyld framing, required to prevent pyld from adding a base IRI to the IDs while framing
options = {
    'base': None
}

# RO-Crate 1.2 context for flattening the entry points (original context is lost during framing)
context_flatten = {
    "@context": "https://w3id.org/ro/crate/1.2/context"
}

# ========================================================================
# define functions for processing the entry points and creating sub-RO-Crates for each entry point

# adds top-level metadata from the original RO-Crate to the entry point metadata if it is missing, to ensure that the entry point metadata is a valid RO-Crate metadata document
def add_top_level_metadata_to_entrypoint(entrypoint, rocrate):
    root_entrypoint = None
    for item in entrypoint["@graph"]:
        if item["@id"] == "./":
            root_entrypoint = item
            break
    if not root_entrypoint:
        return

    root_rocrate = None
    for item in rocrate["@graph"]:
        if item["@id"] == "./":
            root_rocrate = item
            break
    if not root_rocrate:
        return

    if "name" not in root_entrypoint:
        root_entrypoint["name"] = root_rocrate["name"]
    if "description" not in root_entrypoint:
        root_entrypoint["description"] = root_rocrate["description"]
    if "license" not in root_entrypoint:
        root_entrypoint["license"] = root_rocrate["license"]
    if "datePublished" not in root_entrypoint:
        root_entrypoint["datePublished"] = root_rocrate["datePublished"]

# replaces any occurrence of the entry point's root path by "./"
def fix_entrypoint_ids(entrypoint, baseid):
    for item in entrypoint["@graph"]:
        if "@id" in item and item["@id"].startswith(baseid+"/"):
            item["@id"] = item["@id"].replace(baseid, ".")
        elif "@id" in item and item["@id"] == baseid:
            item["@id"] = "./"
        for key, value in item.items():
            if isinstance(value, dict) and "@id" in value and value["@id"].startswith(baseid+"/"):
                value["@id"] = value["@id"].replace(baseid, ".")
            elif isinstance(value, dict) and "@id" in value and value["@id"] == baseid:
                value["@id"] = "./"
            if isinstance(value, list):
                for v in value:
                    if isinstance(v, dict) and "@id" in v and v["@id"].startswith(baseid+"/"):
                        v["@id"] = v["@id"].replace(baseid, ".")
                    elif isinstance(v, dict) and "@id" in v and v["@id"] == baseid:
                        v["@id"] = "./"

# make an entry point graph a valid RO-Crate metadata document
def cratify_entrypoint(entrypoint, rocrate, baseid):
    fix_entrypoint_ids(entrypoint, baseid)
    entrypoint["@graph"].append(default_metadata_obj)
    add_top_level_metadata_to_entrypoint(entrypoint, rocrate)


# ========================================================================
# read and validate the input RO-Crate metadata file

with open(input, 'r') as f_in:
    doc = json.load(f_in)

# profiles = get_profiles()
# for p in profiles:
#     print("Available profile:", p.name, p.identifier, p.path)
# exit()

# check if doc is a valid RO-Crate by validating it with the RO-Crate profile
settings = {}
# settings = {
#     "profile_identifier": "https://w3id.org/ro/crate/1.1"
# }
res = validate_metadata_as_dict(doc, settings)
if res.has_issues():
    print("Input metadata is not a valid RO-Crate according to the RO-Crate 1.1 profile, exiting")
    for check in res.executed_checks:
        cres = res.get_executed_check_result(check)
        success_str = "SUCCESS" if cres else "FAIL"
        print("  - ("+success_str+")", check.name)  # , ": ", check.description)
    exit(1)
settings = {}

# ========================================================================
# frame the RO-Crate metadata to extract entry points (datasets that specify conformsTo)

framed = jsonld.frame(doc, frame, options=options)

# print(json.dumps(framed, indent=2))
# exit()

# iterate potential entry points
entry_points = {}
entrypoint_profile_ids = {}
for item in framed["@graph"]:
    item_has_conformsTo_list = "conformsTo" in item and isinstance(item["conformsTo"], list)
    item_has_conformsTo_url = "conformsTo" in item and isinstance(item["conformsTo"], str)
    item_has_conformsTo_dict = "conformsTo" in item and isinstance(item["conformsTo"], dict)

    if "@id" not in item:
        continue

    id = item["@id"]

    # if conformsTo is a json object, check if it is a profile or matches the specified profile ID
    if item_has_conformsTo_dict:
        if profileID and "@id" in item["conformsTo"] and item["conformsTo"]["@id"] == profileID:
            entry_points[id] = item
            entrypoint_profile_ids[id] = item["conformsTo"]["@id"]
        if not profileID and "@type" in item["conformsTo"]:
            if "Profile" in item["conformsTo"]["@type"] and "CreativeWork" in item["conformsTo"]["@type"]:
                entry_points[id] = item
                entrypoint_profile_ids[id] = item["conformsTo"]["@id"]

    # if conformsTo is a list, check if any of the items in the list are profiles or match the specified profile ID
    if item_has_conformsTo_list:
        for ct in item["conformsTo"]:
            if not isinstance(ct, dict):
                continue
            if profileID and "@id" in ct and ct["@id"] == profileID:
                entry_points[id] = item
                entrypoint_profile_ids[id] = ct["@id"]
            if not profileID and "@type" in ct and isinstance(ct["@type"], list):
                if "Profile" in ct["@type"] and "CreativeWork" in ct["@type"]:
                    entry_points[id] = item
                    entrypoint_profile_ids[id] = ct["@id"]

# for ep in entry_points:
#     print("\n\n\n")
#     print(json.dumps(ep, indent=2))
# exit()

# ========================================================================
# create sub-RO-Crates for each entry point and validate them against the specified profile

# flatten each entry point, making it a valid RO-Crate metadata document
entry_points_flattened = {}
for id, entry_point in entry_points.items():
    entry_point["@context"] = "https://w3id.org/ro/crate/1.2/context"
    flattened = jsonld.flatten(entry_point, context_flatten, options=options)
    cratify_entrypoint(flattened, doc, entry_point["@id"])
    entry_points_flattened[entry_point["@id"]] = flattened

# validate each entry point as a separate RO-Crate metadata document
i = 0
for id, ep in entry_points_flattened.items():
    res = validate_metadata_as_dict(ep, settings)

    print("Found entry point", id, "with profile", entrypoint_profile_ids[id])
    print("Executed", len(res.executed_checks), "checks for entry point", id)
    for check in res.executed_checks:
        cres = res.get_executed_check_result(check)
        success_str = "SUCCESS" if cres else "FAIL"
        print("  - ("+success_str+")", check.name)  # , ": ", check.description)
    if i < len(entry_points_flattened)-1:
        print("\n\n")
    i += 1
