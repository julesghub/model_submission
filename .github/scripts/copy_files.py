"""Copies web material files (images, animations) from issue URLs into the model repository."""

import requests
from github.GithubException import UnknownObjectException


def copy_files(repo, directory, issue_dict):
    """Copy web material files from issue URLs into the specified directory in the repository.

    Iterates over a predefined set of file keys (landing_image, animation,
    graphic_abstract, model_setup_figure). For each key present in issue_dict with a
    non-empty URL, it skips files that already exist in the repo and uploads the rest.

    Args:
        repo: A PyGitHub repository object to upload files into.
        directory (str): The target directory path within the repository.
        issue_dict (dict): A dictionary containing file info keyed by file type.
    """
    file_keys = ["landing_image", "animation", "graphic_abstract", "model_setup_figure"]

    for file_key in file_keys:
        if file_key in issue_dict:
            file_info = issue_dict[file_key]
            url = file_info.get("url", "")

            # Skip if the URL is an empty string
            if url:
                file_path = directory + file_info["filename"]

                # Skip if file already exists in repo
                try:
                    repo.get_contents(file_path)
                    print(f"Skipping {file_key} as the file already exists")
                    continue
                except UnknownObjectException:
                    pass

                response = requests.get(url)
                repo.create_file(file_path, "add " + file_info["filename"], response.content)
            else:
                print(f"Skipping {file_key} as the URL is empty")
