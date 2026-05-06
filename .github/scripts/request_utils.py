import requests
import os
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Base URLs configuration
BASE_URLS = {
    "publication": os.getenv("BASE_URL_PUBLICATION", "https://api.crossref.org/works/"),
    "software": os.getenv("BASE_URL_SOFTWARE", "https://doi.org/"),
    "organization": os.getenv("BASE_URL_ORGANIZATION", "https://api.ror.org/organizations/"),
    "author": os.getenv("BASE_URL_AUTHOR", "https://pub.orcid.org/v3.0/")
}


# Default timeout
TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", 10))

# Initialize a requests session
session = requests.Session()


# Configure retries
max_retries = 3  # Set the maximum number of retries
retry_strategy = Retry(
    total=max_retries,
    status_forcelist=[429, 500, 502, 503, 504],  # Specify which status codes to retry on
    allowed_methods=["HEAD", "GET", "OPTIONS"],  # Use `allowed_methods` for urllib3 v1.26.0 or later
    backoff_factor=1  # Defines the delay between retries
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

def get_record(record_type, record_id):
    """
    BY_AI: Fetches a metadata record from a remote API for the given record type and identifier.

    Constructs the request URL from a lookup table of base URLs keyed by record type
    ('publication', 'software', 'organization', 'author'). Tries fetching with
    'application/ld+json' content type first, then falls back to 'application/json'.
    The session is configured with automatic retries on common transient HTTP errors.

    Parameters:
        record_type (str): The type of record to fetch. Must be one of the keys in
            BASE_URLS ('publication', 'software', 'organization', 'author').
        record_id (str): The identifier for the record (e.g. a DOI, ORCID iD, or ROR ID).

    Returns:
        tuple:
            metadata (dict): The parsed JSON response, or an empty dict if the fetch
                failed.
            log (str): A string containing any errors encountered during fetching.

    Raises:
        ValueError: If record_type is not a supported type.
    """
    log = ""
    metadata = {}

    if record_type not in BASE_URLS:
        raise ValueError(f"Record type `{record_type}` not supported")

    url = BASE_URLS[record_type] + record_id
    print(url)

    # Define content types to try
    content_types = ["application/ld+json", "application/json"]

    for content_type in content_types:
        headers = {"Content-Type": content_type, "Accept": content_type}

        try:
            response = session.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
            response.raise_for_status()  # Raise an exception for HTTP errors

            # If the response is successful and contains content, parse and return the metadata
            if response.content:
                metadata = response.json()
                return metadata, log  # Successful fetch, return immediately

        except requests.exceptions.RequestException as e:
            log += f"Error fetching metadata with {content_type} from {url}: {e}\n"
            # Continue to the next URL or content type

    # If metadata is still empty after all attempts, log an error
    if not metadata:
        log += "Failed to fetch metadata with any content type or URL.\n"

    return metadata, log


def search_organization(org_url):
    """
    BY_AI: Searches the ROR API for an organization matching the given URL and returns its ROR ID.

    Strips the URL scheme and any trailing slash before querying
    'https://api.ror.org/organizations?query.advanced=links:<org_url>'. If exactly one
    result is found the ROR ID is returned; if multiple results are found the first is
    used and a warning is logged.

    Parameters:
        org_url (str): The organization's homepage URL to search for.

    Returns:
        tuple:
            ror_id (str): The ROR identifier URL (e.g. 'https://ror.org/04yx6dh41'), or
                an empty string if no match is found.
            log (str): A string containing informational messages, warnings, or errors
                generated during the search.
    """
    log = ""
    ror_id = ""
    result = {}

    base_url = "https://api.ror.org/organizations"
    org_url = org_url.split("://")[-1]

    #Check if last character is a '/' and if so drop it
    if org_url[-1] == "/": org_url = org_url[:-1]

    url = base_url + '?query.advanced=links:' + org_url
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors

        result = response.json()

    except requests.exceptions.RequestException as e:
        log += f"Error fetching metadata: {e} \n"

    # Deal with response and determine ROR ID
    if result["number_of_results"] == 0:
        log += f"Unable to find ROR for {org_url} \n"
    elif result["number_of_results"] == 1:
        ror_id = result["items"][0]["id"]
        log += f"Found ROR record for {org_url}: {result['items'][0]['name']} ({ror_id}) \n"
        for relation in result["items"][0]["relationships"]:
            if relation["type"] == "Parent":
                log += f"Note: This organization has a parent organization: {relation['label']} ({relation['id']}) \n"
    else:
        ror_id = result["items"][0]["id"]
        log += f"Found more than one ROR record for {org_url}. Assuming the first result is correct; if not please enter the correct ROR. \n"
        for record in result["items"]:
            log += f"\t - {record['name']} ({record['id']}) \n"

    return ror_id, log


def check_uri(uri):
    """
    BY_AI: Checks whether the given URI is reachable via an HTTP GET request.

    Sends an HTTP GET request to the URI and raises an exception for any HTTP error
    status code. Returns 'OK' if the request succeeds, otherwise returns a string
    description of the error.

    Parameters:
        uri (str): The URI to check.

    Returns:
        str: 'OK' if the URI is reachable and returned a success status, otherwise a
            string describing the error that occurred.
    """
    try:
        response = requests.get(uri)
        response.raise_for_status()  # Raise an exception for HTTP errors

        return "OK"

    except Exception as err:
        #return err.args[0]
        return str(err)  # 01/05/24: Convert the error to a string to avoid TypeError when we concatenate to log



def download_license_text(url):
    """
    BY_AI: Downloads and returns the plain-text content of a license from the given URL.

    Sends an HTTP GET request to the provided URL. If the response status is 200, the
    response body is returned as a string. If the request fails or returns a non-200
    status, a fallback message directing the reader to the RO-Crate metadata file is
    returned instead.

    Parameters:
        url (str): The URL from which to download the license text.

    Returns:
        str: The license text if successfully downloaded, or a fallback message string
            if the download fails.
    """
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        else:
            return "# please refer to the metadata file (ro-crate-metadata.json) for information on model license"
    except Exception as e:
        print(f"Error downloading license text: {e}")
        return "please refer to the metadata file (ro-crate-metadata.json) for information on model license"
