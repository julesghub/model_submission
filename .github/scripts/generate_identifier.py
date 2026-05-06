"""Generates a unique model identifier (slug) for the ModelAtlasofTheEarth GitHub organisation."""

import json
import subprocess
import os
import re
from github import Github, Auth


def run_command_check_output(cmd):
    """Run a shell command and return its stdout as bytes.

    Args:
        cmd (str): The shell command to execute.

    Returns:
        bytes: The standard output of the command.
    """
    return subprocess.check_output(cmd, shell=True, stderr=open(os.devnull))


def encode(name, i):
    """Append a numeric suffix to a name when i > 0 to disambiguate identifiers.

    Args:
        name (str): The base model name/slug.
        i (int): The disambiguation index; no suffix is added when 0.

    Returns:
        str: The name with an optional '-<i>' suffix.
    """
    result_str = name
    if i > 0:
        result_str += "-" + str(i)
    return result_str


# Dan added the 'Moved Permanently' condition as a bandaid fix for repos that have been deleted.
# Functionality here may need improvement/rethinking.

def exists(model_id):
    """Check whether a repository already exists in the ModelAtlasofTheEarth GitHub organisation.

    Args:
        model_id (str): The candidate repository name/slug to check.

    Returns:
        bool: True if the repository exists, False if it was not found or has been moved.
    """
    cmd = "curl https://api.github.com/repos/ModelAtlasofTheEarth/{0}".format(model_id)
    output = json.loads(run_command_check_output(cmd))

    if "message" in output:
        return output["message"] not in ("Not Found", "Moved Permanently")
    return True


def choice(name):
    """Return the first available repository name derived from *name* in the ModelAtlasofTheEarth org.

    Tries ``name``, then ``name-1``, ``name-2``, etc., until a name that does not already
    correspond to an existing repository is found.

    Args:
        name (str): The desired base repository name.

    Returns:
        str: A unique repository name that does not currently exist.
    """
    i = 0
    while True:
        model_id = encode(name, i)
        if not exists(model_id):
            return model_id
        i += 1


if __name__ == "__main__":
    token = os.environ.get("GITHUB_TOKEN")
    issue_number = int(os.environ.get("ISSUE_NUMBER"))

    # Get issue
    auth = Auth.Token(token)
    g = Github(auth=auth)
    repo = g.get_repo("ModelAtlasofTheEarth/model_submission")
    issue = repo.get_issue(number=issue_number)

    # Parse issue body
    # Identify headings and subsequent text
    regex = r"### *(?P<key>.*?)\s*[\r\n]+(?P<value>[\s\S]*?)(?=###|$)"
    data = dict(re.findall(regex, issue.body))

    slug = data["-> slug"].strip()
    print(choice(slug))
