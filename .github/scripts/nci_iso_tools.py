class NestedDict(dict):
    def get_nested(self, keys):
        """
        BY_AI: Retrieves a value from a nested dictionary using a dot-separated key path.

        Traverses the dictionary hierarchy by splitting 'keys' on '.' and descending one
        level at a time. Returns an empty dict if any intermediate key is absent.

        Parameters:
            keys (str): A dot-separated string of keys representing the path to the
                desired value (e.g. 'root.license.description').

        Returns:
            The value at the specified path, or an empty dict if any key along the path
            is missing.
        """
        current = self
        for key in keys.split('.'):
            current = current.get(key, {})
        return current

def graph_to_nested_dict(graph):
    """
    BY_AI: Converts a flat RO-Crate '@graph' array into a nested NestedDict keyed by entity ID.

    Iterates over each entity in the graph list and uses its '@id' value as the dictionary
    key. The root entity (whose '@id' is './') is stored under the key 'root'.

    Parameters:
        graph (list of dict): The '@graph' array from an RO-Crate JSON-LD document.

    Returns:
        NestedDict: A dictionary mapping entity IDs (or 'root') to their corresponding
            entity dictionaries.
    """
    nested_dict = NestedDict()
    for item in graph:
        key = 'root' if item["@id"] == './' else item["@id"]
        nested_dict[key] = item
    return nested_dict

def list_to_string(value):
    """
    BY_AI: Converts a list to a comma-separated string, or returns the value unchanged if not a list.

    Parameters:
        value: The value to convert. If it is a list, its items are joined with ', '.
            Otherwise, the value is returned as-is.

    Returns:
        str or original type: A comma-separated string if 'value' is a list, otherwise
            the original value.
    """
    if isinstance(value, list):
        return ', '.join(value)
    return value



def extract_creator_details(ro_crate_nested):
    """
    BY_AI: Extracts a list of creator detail dictionaries from a nested RO-Crate dictionary.

    Reads the 'creator' list from the root entity and builds a standardized detail record
    for each creator, falling back to 'Unknown' for any missing fields.

    Parameters:
        ro_crate_nested (NestedDict): A nested dictionary representation of an RO-Crate,
            as produced by `graph_to_nested_dict`.

    Returns:
        list of dict: A list of dictionaries, each containing the keys 'Last name',
            'First name', 'Organization', 'Email', and 'ORCID ID' for one creator.
    """
    creators = ro_crate_nested.get('root', {}).get('creator', [])
    creator_details = []
    for creator in creators:
        details = {
            "Last name": creator.get("familyName", "Unknown"),  # Default to "Unknown" if not provided
            "First name": creator.get("givenName", "Unknown"),  # Default to "Unknown" if not provided
            "Organization": creator.get("affiliation", {}).get("name", "Unknown") if "affiliation" in creator else "Unknown",
            "Email": creator.get("email", "Unknown"),  # Default to "Unknown" if not provided
            "ORCID ID": creator.get("@id", "Unknown")  # Default to "Unknown" if not provided
        }
        creator_details.append(details)
    return creator_details




def extract_funder_details(ro_crate_nested):
    """
    BY_AI: Extracts a deduplicated list of funder detail dictionaries from a nested RO-Crate dictionary.

    Processes both 'funder' (organisations) and 'funding' (grants) entries from the root
    entity. For each entry it resolves the corresponding full record using its '@id' key
    where available. Grant information is associated with its funder organisation.
    Duplicate funders (identified by name) are removed, and entries with 'Unknown' names
    are excluded from the final result.

    Parameters:
        ro_crate_nested (NestedDict): A nested dictionary representation of an RO-Crate,
            as produced by `graph_to_nested_dict`.

    Returns:
        list of dict: A deduplicated list of dictionaries, each with keys 'name',
            'grant_id', and 'email' for one funder or funding source.
    """
    funders = []

    # Extract 'funder' entries directly using NestedDict indexing
    root_funders = ro_crate_nested.get_nested('root.funder') or []
    for funder in root_funders:
        # Use the funder record directly if it doesn't have an '@id'
        if "@id" in funder:
            funder_details = ro_crate_nested.get(funder["@id"], {})
        else:
            funder_details = funder
        funders.append({
            "name": funder_details.get("name", "Unknown"),
            "grant_id": "No grant ID provided",  # Default text for missing grant IDs
            "email": "Email not provided"  # Default text assuming no email provided
        })

    # Extract 'funding' entries, which are typically grants
    root_fundings = ro_crate_nested.get_nested('root.funding') or []
    for funding in root_fundings:
        if "@id" in funding:
            funding_details = ro_crate_nested.get(funding["@id"], {})
            # Handle nested 'funder' information within 'funding'
            if "funder" in funding_details:
                if "@id" in funding_details["funder"]:
                    funder_info = ro_crate_nested.get(funding_details["funder"]["@id"], {})
                else:
                    funder_info = funding_details["funder"]
                funder_name = funder_info.get("name", "Unknown")
            else:
                funder_name = "Unknown"  # Default text if funder name is not available
            funders.append({
                "name": funder_name,
                "grant_id": funding_details.get("identifier", "No grant ID provided"),
                "email": "Email not provided"  # Default text assuming no email provided
            })

    # Deduplicate funders based on 'name'
    unique_funders = {funder['name']: funder for funder in funders if funder['name'] != "Unknown"}
    return list(unique_funders.values())
