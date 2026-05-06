import os
import re
import requests
import filetype
import subprocess
from filetypes import Svg

from request_utils import get_record, search_organization
from parse_metadata_utils import parse_author, parse_organization


def validate_slug(proposed_slug):
    """Validate the proposed model slug and return a safe identifier.

    Checks that the slug is in the format ``familyname-year-keyword`` where *year* is
    a four-digit number, then verifies that a repository with the proposed name can
    actually be created (via :func:`generate_identifier`).

    Args:
        proposed_slug (str): The slug string entered by the submitter.

    Returns:
        tuple: A ``(slug, error_log)`` tuple where *slug* is the validated (or
        best-available) slug string and *error_log* accumulates any warnings or errors.
    """

    error_log = ""

    try:
        slug_bits = proposed_slug.split("-")
        assert len(slug_bits) == 3, "Warning: slug should be in the format `familyname-year-keyword`\n"
        assert len(slug_bits[1]) == 4, "Warning: year should be in the format `yyyy`\n"
        int(slug_bits[1])
    except ValueError:
        error_log += "Warning: slug should be in the format `familyname-year-keyword` where year is a number in the format `yyyy`\n"
    except AssertionError as err:
        error_log += f"{err}\n"

    #try a workaround for local tests
    cmd = "python3 .github/scripts/generate_identifier.py"

    #if os.path.exists('../.github/scripts/generate_identifier.py'):
    #    os.path.exists('../.github/scripts/generate_identifier.py')

    try:
        slug = subprocess.check_output(cmd, shell=True, text=True, stderr=open(os.devnull)).strip()
        if proposed_slug != slug:
            error_log += f"Warning: Model repo cannot be created with proposed slug `{proposed_slug}`. \n"
            error_log += f"Either propose a new slug or repo will be created with name `{slug}`. \n"
    except Exception as err:
        slug = ""
        error_log += "Error: Unable to create valid repo name... \n"
        error_log += f"`{err}`\n"

    return slug, error_log


def parse_name_or_orcid(name_or_orcid):
    """
    Distinguishes between a name and an ORCID ID, returning the corresponding author record.

    Parameters:
    name_or_orcid (str): The input string which could be either a name in the format 'last name(s), first name(s)' or an ORCID ID.

    Returns:
    dict: Author record.
    str: Error log.
    """
    error_log = ""
    orcid_id = extract_orcid(name_or_orcid)

    if orcid_id:
        orcid_record, log1 = get_record("author", orcid_id)
        author_record, log2 = parse_author(orcid_record)
        if log1 or log2:
            error_log += log1 + log2
        # Extract the name if present
        name_part = re.sub(r'\(.*?\)|\[.*?\]', '', name_or_orcid).strip()
        if name_part:
            try:
                familyName, givenName = [name.strip() for name in re.split(r',\s*', name_part)]
                author_record["givenName"] = givenName
                author_record["familyName"] = familyName
            except ValueError:
                pass  # Ignore name extraction errors
    else:
        try:
            familyName, givenName = [name.strip() for name in re.split(r',\s*', name_or_orcid)]
            author_record = {
                "@type": "Person",
                "givenName": givenName,
                "familyName": familyName,
            }
        except ValueError:
            error_log += f"- Error: name `{name_or_orcid}` in unexpected format. Expected `last name(s), first name(s)` or ORCID.\n"
            author_record = {}

    return author_record, error_log


def parse_yes_no_choice(input):
    '''
    Return True if the input string contains an 'x' (case-insensitive), False otherwise.

    Args:
        input (str): A string representing a yes/no checkbox value.

    Returns:
        bool: True if 'x' is present in the lowercased input, False otherwise.
    '''
    return "x" in input.lower()

def is_orcid_format(author):
    """Check whether *author* is a bare ORCID identifier (without the URL prefix).

    Args:
        author (str): The string to test.

    Returns:
        bool: True if *author* matches the pattern ``XXXX-XXXX-XXXX-XXXX``, False otherwise.
    """
    orcid_pattern = re.compile(r'\d{4}-\d{4}-\d{4}-\d{3}[0-9X]')
    return bool(orcid_pattern.fullmatch(author))


def get_authors(author_list):
    '''
    Parses a list of author names or ORCID iDs and returns a list of dictionaries of schema.org Person type

        Parameters:
            author_list (list of strings): list of names in format Last Name(s), First Name(s) and/or ORCID iDs

        Returns:
            authors (list of dicts)
            log (string)

    '''

    log = ""
    authors = []

    for author in author_list:
        author_record, error_log = parse_name_or_orcid(author)
        if author_record:
            authors.append(author_record)
        if error_log:
            log += error_log

    return authors, log


def get_funders(funder_list):
    """Resolve a list of funder names or ROR URLs to schema.org Organization dicts.

    For each entry in *funder_list*:

    * If the entry contains ``ror.org``, the ROR ID is extracted and the ROR API is
      queried to build a structured Organization record.
    * Otherwise, the ROR API is searched by URL/name to obtain a ROR ID first.

    Args:
        funder_list (list[str]): A list of funder identifiers (ROR URLs, website URLs,
            or plain organisation names).

    Returns:
        tuple: A ``(funders, log)`` tuple where *funders* is a list of Organisation dicts
        and *log* is a string accumulating warnings or errors.
    """

    log = ""
    funders = []

    for funder in funder_list:
        # Step 1: Try to resolve name or URL
        if "ror.org" not in funder:
            ror_id, get_log = search_organization(funder)
            log += get_log
            if not ror_id:
                funders.append({"@type": "Organization", "name": funder, "url": funder})
                continue
            funder = ror_id

        # Step 2: Handle ROR.org IDs properly
        if "ror.org" in funder:
            ror_id = funder.rstrip("/").split("/")[-1]
            ror_url = f"https://ror.org/{ror_id}"

            record, get_log = get_record("organization", ror_id)
            funder_record, parse_log = parse_organization(record)
            log += get_log + parse_log

            if not funder_record:
                funder_record = {"@type": "Organization", "@id": ror_url, "name": ""}
            else:
                funder_record["@id"] = ror_url

            funders.append(funder_record)

    return funders, log





#Modification to deal with pdf better
#original function above
def parse_image_and_caption_old2(img_string, default_filename):
    log = ""
    image_record = {}

    # Regex to match Markdown image syntax
    md_regex = r"\[(?P<filename>.*?)\]\((?P<url>.*?)\)"
    # Regex to match HTML image syntax
    html_regex = r'alt="(?P<filename>[^"]+)" src="(?P<url>[^"]+)"'
    # Pattern to identify the URL structure
    pattern = re.compile(r"https://github.com/ModelAtlasofTheEarth/[^/]+/assets/|https://github.com/ModelAtlasofTheEarth/[^/]+/files/")

    # Adding support for SVG files
    filetype.add_type(Svg())

    caption = []

    # Split the input string by line
    for string in img_string.split("\r\n"):
        # Check if the line contains the expected URL pattern
        if pattern.search(string):
            try:
                # Try to match the Markdown image format
                image_record = re.search(md_regex, string).groupdict()
            except:
                if string.startswith("https://"):
                    # If it is a URL, use the default filename
                    image_record = {"filename": default_filename, "url": string}
                elif "src" in string:
                    # Try to match the HTML image format
                    image_record = re.search(html_regex, string).groupdict()
                else:
                    log += "Error: Could not parse image file and caption\n"
        else:
            caption.append(string)

    # If the file is not an image but a document (e.g., PDF), handle it separately
    if "url" in image_record:
        response = requests.get(image_record["url"])
        content_type = response.headers.get("Content-Type")
        if content_type.startswith("image"):
            image_record["filename"] += "." + filetype.get_type(mime=content_type).extension
        else:
            # For non-image files, use the original filename without modification
            image_record["filename"] = image_record["filename"]

    # Join the collected caption lines into a single string
    image_record["caption"] = "\n".join(caption)

    if not caption:
        log += "Error: No caption found for image.\n"

    return image_record, log


def parse_image_and_caption_old(img_string, default_filename):
    log = ""
    image_record = {}

    # Precompile regex patterns
    md_regex = re.compile(r"\[(?P<filename>.*?)\]\((?P<url>.*?)\)")
    html_regex = re.compile(r'alt="(?P<filename>[^"]+)" src="(?P<url>[^"]+)"')

    # Combined pattern to match both the old and new GitHub URL structures
    pattern = re.compile(r"https://github.com/(?:ModelAtlasofTheEarth/[^/]+/(?:assets|files)/|user-attachments/assets/)")

    # Adding support for SVG files
    filetype.add_type(Svg())

    caption = []

    for string in img_string.split("\r\n"):
        if pattern.search(string):
            try:
                # Try to match the Markdown image format
                image_record = md_regex.search(string).groupdict()
            except AttributeError:
                if string.startswith("https://"):
                    image_record = {"filename": default_filename, "url": string}
                elif "src" in string:
                    try:
                        image_record = html_regex.search(string).groupdict()
                    except AttributeError:
                        log += f"Error: Could not parse HTML image format for line: {string}\n"
                else:
                    log += f"Error: Could not parse image file and caption for line: {string}\n"
        else:
            caption.append(string)

    if "url" in image_record:
        response = requests.get(image_record["url"])
        content_type = response.headers.get("Content-Type", "")

        if content_type.startswith("image"):
            # Ensure file extension is not duplicated
            extension = filetype.get_type(mime=content_type).extension
            if not image_record["filename"].endswith(f".{extension}"):
                image_record["filename"] += f".{extension}"
        else:
            log += f"Warning: File is not an image (Content-Type: {content_type}).\n"

    image_record["caption"] = "\n".join(caption)

    if not caption:
        log += "Error: No caption found for image.\n"

    return image_record, log

# Local cache for URL responses
url_cache = {}

def parse_image_and_caption(img_string, default_filename):
    log = ""
    image_record = {"filename": None, "url": "", "caption": ""}

    # Precompile regex patterns for Markdown image links
    md_regex = re.compile(r"\[(?P<filename>[^]]+)\]\((?P<url>https?://[^\s)]+)\)")
    
    # Combined pattern to match both old and new GitHub URL structures
    pattern = re.compile(r"https://github.com/(?:ModelAtlasofTheEarth/[^/]+/(?:assets|files)/|user-attachments/assets/)")

    # Adding support for SVG files
    filetype.add_type(Svg())

    caption = []

    # Split lines and check for patterns
    for line in img_string.splitlines():
        # Check if the line matches the Markdown pattern for image links
        md_match = md_regex.search(line)  
        if md_match:
            # Extract filename and URL
            image_record["filename"] = md_match.group("filename").strip()  # Strip whitespace
            image_record["url"] = md_match.group("url").strip()  # Strip whitespace
        elif pattern.search(line):
            # Fallback for direct URL parsing (though this shouldn't be necessary now)
            if line.startswith("https://"):
                image_record["filename"] = default_filename
                image_record["url"] = line
        else:
            # Accumulate the caption lines, trimming whitespace
            caption.append(line.strip())

    # Join the caption lines
    if caption:
        image_record["caption"] = " ".join(caption)
    else:
        log += "Error: No caption found for image.\n"

    # Check if URL is available
    if image_record["url"]:
        # Check if the URL is already cached
        if image_record["url"] in url_cache:
            content_type = url_cache[image_record["url"]]
        else:
            try:
                response = requests.get(image_record["url"], timeout=5)  # Set a timeout for requests
                content_type = response.headers.get("Content-Type", "")
                url_cache[image_record["url"]] = content_type  # Cache the response content type
            except requests.RequestException as e:
                log += f"Error: Failed to download image. {str(e)}\n"
                content_type = ""

        if content_type.startswith("image"):
            # Ensure the file extension is not duplicated
            extension = filetype.get_type(mime=content_type).extension
            if not image_record["filename"].endswith(f".{extension}"):
                image_record["filename"] += f".{extension}"
        else:
            log += f"Warning: File is not an image (Content-Type: {content_type}).\n"

    # Images and animations go in 'graphics/' directory
    if (
        image_record["filename"] is not None
        and image_record["filename"] != ""
        and not image_record["filename"].startswith("graphics/")):
        image_record["filename"] = "graphics/" + image_record["filename"]
    if image_record["filename"] == "":
        image_record["filename"] = None
    return image_record, log

def extract_doi_parts(doi_string):
    # Regular expression to match a DOI within a string or URL
    # It looks for a string starting with '10.' followed by any non-whitespace characters
    # and optionally includes common URL prefixes
    # the DOI
    doi_pattern = re.compile(r'(10\.[0-9]+/[^ \s]+)')

    # Search for DOI pattern in the input string
    match = doi_pattern.search(doi_string)

    # If a DOI is found in the string
    if match:
        # Extract the DOI
        doi = match.group(1)

        # Clean up the DOI by removing any trailing characters that are not part of a standard DOI
        # This includes common punctuation and whitespace that might be accidentally included
        #doi = re.sub(r'[\s,.:;]+$', '', doi)
        doi = re.sub(r'[\s,.:;|\/\?:@&=+\$,]+$', '', doi)

        # Split the DOI into prefix and suffix at the first "/"
        #prefix, suffix = doi.split('/', 1)

        return doi
    else:
        # Return an error message if no DOI is found
        return "No valid DOI found in the input string."


def extract_orcid(input_str):
    """
    Extracts an ORCiD ID from a given string.

    The function accepts a string that can either be a direct ORCiD ID or an ORCiD URL.
    It attempts to extract the ORCiD ID using a regular expression that matches both formats.
    If a valid ORCiD ID is found, it is returned. If no valid ID is found, the function returns None.

    Parameters:
    - input_str (str): A string containing a potential ORCiD ID or ORCiD URL.

    Returns:
    - str: The extracted ORCiD ID if found, otherwise None.

    Raises:
    - None: The function does not explicitly raise any errors but returns None for invalid inputs.

    Example usage:
    >>> extract_orcid("http://orcid.org/0000-0003-2198-9172")
    '0000-0003-2198-9172'

    >>> extract_orcid("0000-0002-1825-0097")
    '0000-0002-1825-0097'

    >>> extract_orcid("John Doe")  # Invalid input
    None
    """

    orcid_pattern = re.compile(r'\d{4}-\d{4}-\d{4}-\d{3}[0-9X]')
    match = orcid_pattern.search(input_str)
    if match:
        return match.group(0)
    return None


def is_orcid(input_str):
    """
    Checks if the given string matches the ORCiD pattern.

    Parameters:
    - input_str (str): A string to be checked against the ORCiD pattern.

    Returns:
    - bool: True if the string matches the ORCiD pattern, False otherwise.
    """
    orcid_pattern = re.compile(r'(?:https?://orcid\.org/)?([0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X])')
    return bool(orcid_pattern.match(input_str))

def remove_duplicates(list_a, list_b):
    """
    Removes items from list_b that have an @id matching any @id in list_a. If an @id is an ORCiD pattern,
    it is first normalized using extract_orcid. Otherwise, the @id is used as is.

    Parameters:
    - list_a (list): List of dictionaries potentially containing ORCiD IDs in their '@id' keys.
    - list_b (list): List of dictionaries from which items should be removed if their '@id' matches any in list_a.

    Returns:
    - list: A new list derived from list_b with items removed that have matching @id keys in list_a.
    """
    # Normalize and collect @id values from list_a
    a_ids = set()
    for item in list_a:
        if '@id' in item:
            id_val = item['@id']
            if is_orcid(id_val):
                a_ids.add(extract_orcid(id_val))
            else:
                a_ids.add(id_val)

    # Filter list_b based on @id values found in a_ids
    filtered_b_list = []
    for item in list_b:
        if '@id' in item:
            id_val = item['@id']
            normalized_id = extract_orcid(id_val) if is_orcid(id_val) else id_val
            if normalized_id not in a_ids:
                filtered_b_list.append(item)

    return filtered_b_list


def parse_size(size_str, base_unit=1024):

    """
    Parse a human-readable size string into bytes.

    Args:
        size_str (str): The size string to parse (e.g. "1KB", "2MB", etc.)
        base_unit (int, optional): The base unit to use for calculations (default: 1024)

    Returns:
        tuple: A tuple containing the parsed value (or None if it can't be parsed) and an error log string
    """

    error_log = ""
    value = None
    try:
        size_str = size_str.replace(" ", "")  # remove spaces
        match = re.search(r"(\d+)(~?)([kKmMgGtTpP]?[bB]?)", size_str)
        if match:
            value = int(match.group(1))
            unit = match.group(3).upper()
            units = {
                "KB": 1,
                "MB": 2,
                "GB": 3,
                "TB": 4,
                "PB": 5,
                "K": 1,
                "M": 2,
                "G": 3,
                "T": 4,
                "P": 5
            }
            value = value * (base_unit ** units.get(unit, 0))
        else:
            error_log = "Invalid size string"
    except ValueError as e:
        error_log = str(e)
    #print(value, error_log)
    return value, error_log

def process_funding_data(input_string):
    """
    Processes an input string containing research funding data to extract information about funders and their grants.
    """
    schema_funders = []
    schema_funding = []

    for line in input_string.split('\n'):
        if not line.strip():
            continue
        parts = line.split(',', 1)
        funder_info = parts[0].strip()
        grant_number = parts[1].strip() if len(parts) > 1 else None

        # Determine funder type
        if re.match(r'^https?:\/\/ror\.org\/', funder_info):
            # ✅ Ensure ROR ID is clean before lookup
            ror_id = funder_info.rstrip('/').split('/')[-1]
            funder_info = f"https://ror.org/{ror_id}"
            results, log = get_funders([funder_info])
            organization = results[0] if isinstance(results, list) and results else {'@type': 'Organization', 'name': ''}
        elif re.match(r'^https?:\/\/', funder_info):
            try:
                ror = search_organization(funder_info)
                results, log = get_funders([funder_info])
                organization = results[0] if isinstance(results, list) and results else {'@type': 'Organization', 'name': ''}
            except Exception:
                organization = {'@type': 'Organization', '@id': funder_info, 'name': ''}
                log = "Can't find funding Organisation"
        else:
            organization = {'@type': 'Organization', 'name': funder_info}

        # Associate grants
        if grant_number:
            schema_funding.append({
                '@type': 'Grant',
                'funder': organization,
                'identifier': grant_number
            })
        else:
            schema_funders.append(organization)

        # Merge unique funders
        for funding_entry in schema_funding:
            if funding_entry['funder'] not in schema_funders:
                schema_funders.append(funding_entry['funder'])

    return {'funders': schema_funders, 'funding': schema_funding}

def identify_separator(input_string):
    # Strip leading and trailing whitespace and split by newline to get lines
    lines = input_string.strip().split('\n')

    # Count the number of commas and newlines
    comma_count = sum(line.count(',') for line in lines)
    newline_count = len(lines) - 1

    # Heuristics: more commas than newlines => CSV
    if comma_count > newline_count:
        return 'csv'
    else:
        return 'newline'

def separate_string(input_string):
    separator_type = identify_separator(input_string)

    if separator_type == 'csv':
        return [x.strip() for line in input_string.strip().split('\n') for x in line.split(',')]
    elif separator_type == 'newline':
        return [line.strip() for line in input_string.strip().split('\n') if line]
