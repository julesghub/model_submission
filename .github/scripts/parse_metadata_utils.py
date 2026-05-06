def parse_author(metadata):
    """Parse an ORCID or raw author metadata record into a schema.org Person dict.

    If *metadata* already contains ``@type`` and ``@id`` keys it is returned as-is.
    Otherwise the function attempts to build a Person record from the raw ORCID API
    JSON structure.

    Args:
        metadata (dict): An ORCID API JSON record or an already-parsed json-ld Person dict.

    Returns:
        tuple: A ``(author_record, log)`` tuple where *author_record* is a dict and
        *log* is a string describing any warnings or errors.
    """
    log = ""
    author_record = {}

    if "@type" in metadata and "@id" in metadata:
        author_record = metadata
        log += "ORCID metadata record succesfully extracted in json-ld format \n"

    else:

        try:
            author_record = {
                "@type": "Person",
                "@id": metadata["orcid-identifier"]["uri"],
                "givenName": metadata['person']['name']['given-names']['value'],
                "familyName": metadata['person']['name']['family-name']['value'],
            }

            affiliation_list = []
            for affiliation in metadata["activities-summary"]["employments"]["affiliation-group"]:
                summary = affiliation["summaries"][0]["employment-summary"]
                if summary["end-date"] is None:
                    affiliation_list.append({"@type": "Organization", "name": summary["organization"]["name"]})

            if affiliation_list:
                author_record["affiliation"] = affiliation_list

        except Exception as err:
            log += "Error: unable to parse author metadata. \n"
            log += f"`{err}`\n"

    return author_record, log

def parse_organization(record):
    """
    Parses a ROR organization record into a schema.org Organization dict.
    Handles both legacy and current ROR formats.
    """
    log = ""

    if not record or "id" not in record:
        return {}, "Error: invalid or empty organization record.\n"

    try:
        org = {"@type": "Organization"}
        org["@id"] = record.get("id")

        # ✅ Handle modern ROR format (name inside 'names' list)
        if "name" in record and isinstance(record["name"], str):
            org["name"] = record["name"]
        elif "names" in record and isinstance(record["names"], list) and record["names"]:
            org["name"] = record["names"][0].get("value", "")
        else:
            org["name"] = "(unknown name)"
            log += "Warning: missing name field.\n"

        # Add homepage if available
        links = record.get("links", [])
        if links:
            if isinstance(links[0], dict):
                org["url"] = links[0].get("value")
            else:
                org["url"] = links[0]

        # Add organization types if available
        if record.get("types"):
            org["additionalType"] = record["types"]

        return org, log

    except Exception as e:
        return {}, f"Error: unable to parse organization metadata.\n`{e}`\n"


def parse_software(metadata, doi):
    """Parse a DOI metadata record into a schema.org SoftwareApplication dict.

    If *metadata* already contains ``@type`` and ``@id`` keys it is returned as-is.
    Otherwise the function attempts to build a SoftwareApplication record from the
    raw Zenodo/DataCite JSON structure.

    Args:
        metadata (dict): A DOI metadata record or an already-parsed json-ld dict.
        doi (str): The DOI/URL to use as the ``@id`` when building a new record.

    Returns:
        tuple: A ``(software_record, log)`` tuple where *software_record* is a dict
        and *log* is a string describing any warnings or errors.
    """
    log = ""
    software_record = {}

    # here we check if software metadata was found in json-ld
    # if so, we simply return the record
    if "@type" in metadata and "@id" in metadata:
        software_record = metadata
        log += "doi.org metadata record succesfully extracted in json-ld format \n"

    # if not, we'll try to build a schema.org entity from the json
    else:
        software_record["@type"] = "SoftwareApplication"
        software_record["@id"] = doi
        found_something = False
        if "title" in metadata:
            software_record["name"] = metadata["title"]
            print('found title')
            found_something = True
        if "metadata" in metadata:
            if "version" in metadata["metadata"]:
                software_record["softwareVersion"] = metadata["metadata"]["version"]
                found_something = True

            author_list = []
            if "creators" in metadata["metadata"]:
                for author in metadata["metadata"]["creators"]:
                    author_record = {"@type": "Person"}
                    if "orcid" in author:
                        author_record["@id"] = author["orcid"]
                    if "givenName" in author:
                        author_record["givenName"] = author["given"]
                        author_record["familyName"] = author["family"]
                    elif "name" in author:
                        author_record["name"] = author["name"]
                    if "affiliation" in author:
                        author_record["affiliation"] = author["affiliation"]

                    author_list.append(author_record)

            if author_list:
                found_something = True
                software_record["author"] = author_list


        if not found_something:
            log += "Error: unable to parse software metadata. \n"

    return software_record, log

def parse_publication(metadata):
    """Parse a Crossref API metadata record into a schema.org ScholarlyArticle dict.

    If *metadata['message']* already contains ``@type`` and ``@id`` keys it is returned
    as-is. Otherwise the function attempts to build a ScholarlyArticle record from the
    raw Crossref JSON structure.

    Args:
        metadata (dict): The full Crossref API response containing a ``'message'`` key.

    Returns:
        tuple: A ``(publication_record, log)`` tuple where *publication_record* is a dict
        and *log* is a string describing any warnings or errors.
    """
    log = ""
    publication_record = {}

    metadata = metadata['message']

    if "@type" in metadata and "@id" in metadata:
        publication_record = metadata
        log += "Crossref metadata record succesfully extracted in json-ld format \n"
    else:
        try:
            publication_record = {
                "@type": "ScholarlyArticle",
                "@id": metadata["URL"],
                "name": metadata["title"][0],
                }

            if "issue" in metadata:
                publication_issue = {
                    "@type": "PublicationIssue",
                    "issueNumber": metadata["issue"],
                    "datePublished": '-'.join(map(str,metadata["published"]["date-parts"][0])),
                    "isPartOf": {
                        "@type": [
                            "PublicationVolume",
                            "Periodical"
                        ],
                        "name": metadata["container-title"],
                        "issn": metadata["ISSN"],
                        "volumeNumber": metadata["volume"],
                        "publisher": metadata["publisher"]
                    },
                },

                publication_record["isPartOf"] = publication_issue
            else:
                if metadata["published"]:
                    publication_record["datePublished"] = '-'.join(map(str,metadata["published"]["date-parts"][0]))
                if metadata["publisher"]:
                    publication_record["publisher"] = metadata["publisher"]

            author_list = []

            for author in metadata["author"]:
                author_record = {"@type": "Person"}
                if "ORCID" in author:
                    author_record["@id"] = author["ORCID"]
                author_record["givenName"] = author["given"]
                author_record["familyName"] = author["family"]

                affiliation_list = []
                for affiliation in author["affiliation"]:
                    affiliation_list.append({"@type": "Organization", "name": affiliation["name"]})

                if affiliation_list:
                    author_record["affiliation"] = affiliation_list

                author_list.append(author_record)

            if author_list:
                publication_record["author"] = author_list

            if "abstract" in metadata:
                publication_record["abstract"] = metadata["abstract"].split('<jats:p>')[1].split('</jats:p>')[0]

            if "page" in metadata:
                publication_record["pagination"] = metadata["page"]

            if "alternative-id" in metadata:
                publication_record["identifier"] = metadata["alternative-id"]

            if "funder" in metadata:
                funder_list = []
                for funder in metadata["funder"]:
                    funder_list.append({"@type": "Organization", "name": funder["name"]})
                publication_record["funder"] = funder_list

        except Exception as err:
            log += "Error: unable to parse publication metadata. \n"
            log += f"`{err}`\n"

    return publication_record, log
