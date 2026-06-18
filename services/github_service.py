"""GitHub Service module.

Interfaces with the GitHub API to fetch repository structures, file contents,
issue lists, and pull request information, or clones repositories locally.
"""

import os
import shutil
import subprocess
import urllib.parse
import logging
from typing import Dict, List, Any, Optional
import requests

logger = logging.getLogger(__name__)


class InvalidGitHubRepoURLError(ValueError):
    """Raised when the provided repo URL/identifier is not a supported GitHub format."""


class RepositoryNotFoundError(RuntimeError):
    """Raised when the target repository cannot be found (404-like git clone failure)."""


class BranchNotFoundError(ValueError):
    """Raised when the requested branch/ref does not exist in the repository."""


class GitHubService:
    """Wrapper class containing helpers to query GitHub repositories or clone them locally."""

    def __init__(self, token: Optional[str] = None) -> None:
        """Initializes the GitHub client with an optional authentication token.

        Args:
            token: GitHub Personal Access Token (PAT).
        """
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.session = requests.Session()
        if self.token:
            self.session.headers.update({"Authorization": f"token {self.token}"})
        self.session.headers.update({"Accept": "application/vnd.github.v3+json"})

    def parse_repo_url(self, repo_url: str) -> Dict[str, str]:
        """Parses repository URL into owner and repo name.

        Args:
            repo_url: Repository URL or owner/repo identifier.

        Returns:
            A dictionary containing "owner" and "repo".
        """
        url = repo_url.strip()
        if url.endswith(".git"):
            url = url[:-4]
        
        # Strip trailing slash if present
        if url.endswith("/"):
            url = url[:-1]

        if "github.com/" in url:
            parts = url.split("github.com/")[-1].split("/")
            if len(parts) >= 2:
                return {"owner": parts[0], "repo": parts[1]}
        
        # If it's already in owner/repo format
        parts = url.split("/")
        if len(parts) == 2:
            return {"owner": parts[0], "repo": parts[1]}
            
        raise ValueError(f"Invalid GitHub repository URL: {repo_url}")

    def get_local_repo_path(self, repo_fullName: str) -> str:
        """Returns the local path where a repository is or should be cloned.

        Args:
            repo_fullName: GitHub owner/repo identifier.

        Returns:
            The local directory path.
        """
        # We store cloned repos in a directory under the current project's data directory
        base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cloned_repos")
        safe_name = repo_fullName.replace("/", "_")
        return os.path.join(base_dir, safe_name)

    def clone_repository(self, repo_url: str, branch: Optional[str] = None) -> str:
        """Clones a GitHub repository to a local directory using Git CLI.

        Args:
            repo_url: GitHub repository URL or owner/repo identifier.
            branch: Optional branch/ref name to clone. If provided, existence is validated.

        Returns:
            The local path to the cloned repository.
        """
        try:
            parsed = self.parse_repo_url(repo_url)
        except ValueError as e:
            raise InvalidGitHubRepoURLError(str(e))

        repo_fullName = f"{parsed['owner']}/{parsed['repo']}"
        dest_dir = self.get_local_repo_path(repo_fullName)

        # Prepare URL with token if available to handle private repos
        clone_url = repo_url
        if self.token:
            parsed_url = urllib.parse.urlparse(repo_url)
            if parsed_url.scheme == "https":
                netloc = f"{self.token}@{parsed_url.netloc}"
                clone_url = urllib.parse.urlunparse(parsed_url._replace(netloc=netloc))
            elif not parsed_url.scheme:
                # If it's owner/repo format, build the https clone URL
                clone_url = f"https://{self.token}@github.com/{repo_fullName}.git"
        elif not urllib.parse.urlparse(repo_url).scheme:
            # If it's owner/repo format and no token
            clone_url = f"https://github.com/{repo_fullName}.git"

        # Validate branch existence (when requested) before cloning
        if branch:
            # Use ls-remote against the remote to confirm refs exist.
            # --heads ensures branch refs only.
            cmd_check = ["git", "ls-remote", "--heads", clone_url, branch]
            res_check = subprocess.run(cmd_check, capture_output=True, text=True, check=False)
            if res_check.returncode != 0:
                err_msg = res_check.stderr.replace(self.token, "********") if self.token else res_check.stderr
                # For safety treat nonzero as missing branch (API will return 400/422).
                raise BranchNotFoundError(f"Failed to validate branch '{branch}' for {repo_fullName}: {err_msg.strip()}")
            if not res_check.stdout.strip():
                raise BranchNotFoundError(f"Branch '{branch}' does not exist for repository {repo_fullName}.")

        # Remove existing directory if it exists
        if os.path.exists(dest_dir):
            try:
                if os.name == "nt":
                    subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", dest_dir], check=False)
                else:
                    shutil.rmtree(dest_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Failed to completely remove existing directory {dest_dir}: {e}.")

        os.makedirs(os.path.dirname(dest_dir), exist_ok=True)

        logger.info(f"Cloning repository {repo_fullName} to {dest_dir}...")
        cmd = ["git", "clone", "--depth", "1", "--single-branch"]
        if branch:
            cmd.extend(["--branch", branch])
        cmd.extend([clone_url, dest_dir])

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            err_msg = result.stderr.replace(self.token, "********") if self.token else result.stderr
            lower = (result.stderr or "").lower()
            # Heuristics for 404-like cases
            if any(s in lower for s in ["not found", "repository not found", "fatal: repository", "could not read from remote repository"]):
                raise RepositoryNotFoundError(f"Repository {repo_fullName} not found. {err_msg.strip()}")
            raise RuntimeError(f"Failed to clone repository: {err_msg}")

        return dest_dir

    def extract_source_files(self, local_path: str) -> List[Dict[str, Any]]:
        """Walks the cloned repository and extracts files, skipping ignored ones.

        Args:
            local_path: Local path to the repository.

        Returns:
            A list of dictionary records containing file paths and contents.
        """
        ignored_names = {"node_modules", ".git", "dist", "build", ".next", "venv", "__pycache__"}
        extracted_files = []
        
        for root, dirs, files in os.walk(local_path):
            # Prune ignored directories in-place
            dirs[:] = [d for d in dirs if d not in ignored_names]
            
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, local_path)
                
                # Check if file path parts contain ignored directory names
                parts = rel_path.split(os.sep)
                if any(part in ignored_names for part in parts):
                    continue
                    
                # Skip binary and media formats
                ext = os.path.splitext(file)[1].lower()
                if ext in {
                    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".tar", ".gz",
                    ".mp3", ".mp4", ".woff", ".woff2", ".ttf", ".eot", ".svg", ".pyc",
                    ".db", ".sqlite", ".exe", ".bin", ".dll", ".so", ".dylib", ".pkl", ".h5"
                }:
                    continue
                    
                # Read content as text
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    extracted_files.append({
                        "path": rel_path.replace(os.sep, "/"),
                        "content": content
                    })
                except Exception as e:
                    logger.debug(f"Skipping file {rel_path} due to read error: {e}")
                    
        return extracted_files

    def fetch_repository_files(self, repo_fullName: str, branch: str = "main") -> List[Dict[str, Any]]:
        """Queries the local repository clone or fallback API to get all file metadata recursively.

        Args:
            repo_fullName: GitHub owner/repo identifier (e.g., "google/guava").
            branch: Target branch name.

        Returns:
            A list of dictionary records containing file paths, types, sizes, and URLs.
        """
        dest_dir = self.get_local_repo_path(repo_fullName)
        
        # If not cloned, clone it
        if not os.path.exists(dest_dir):
            repo_url = f"https://github.com/{repo_fullName}.git"
            try:
                self.clone_repository(repo_url)
            except Exception as e:
                logger.error(f"Clone failed inside fetch_repository_files: {e}")
                raise

        files_meta = []
        ignored_names = {"node_modules", ".git", "dist", "build", ".next", "venv", "__pycache__"}
        
        for root, dirs, files in os.walk(dest_dir):
            dirs[:] = [d for d in dirs if d not in ignored_names]
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, dest_dir).replace(os.sep, "/")
                if any(part in ignored_names for part in rel_path.split("/")):
                    continue
                size = os.path.getsize(file_path)
                files_meta.append({
                    "path": rel_path,
                    "type": "blob",
                    "size": size,
                    "url": f"https://github.com/{repo_fullName}/blob/{branch}/{rel_path}"
                })
        return files_meta

    def fetch_file_content(self, repo_fullName: str, file_path: str, ref: str = "main") -> str:
        """Downloads/reads the raw content of a specific file from a GitHub repository clone.

        Args:
            repo_fullName: GitHub owner/repo identifier.
            file_path: Relative path to the file.
            ref: Git commit or branch ref.

        Returns:
            The raw text content of the file.
        """
        dest_dir = self.get_local_repo_path(repo_fullName)
        local_file = os.path.join(dest_dir, file_path.replace("/", os.sep))
        
        if os.path.exists(local_file):
            try:
                with open(local_file, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except Exception as e:
                raise IOError(f"Error reading file {file_path} from local storage: {e}")
        
        # If not found locally, try to fetch via GitHub API
        url = f"https://api.github.com/repos/{repo_fullName}/contents/{file_path}?ref={ref}"
        try:
            resp = self.session.get(url)
            resp.raise_for_status()
            data = resp.json()
            if "content" in data and data.get("encoding") == "base64":
                import base64
                return base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
            elif "download_url" in data:
                raw_resp = requests.get(data["download_url"])
                raw_resp.raise_for_status()
                return raw_resp.text
        except Exception as e:
            logger.error(f"Failed to fetch remote file content for {file_path}: {e}")
            
        raise FileNotFoundError(f"File {file_path} not found locally or remotely for repository {repo_fullName}.")

    def fetch_issues(self, repo_fullName: str, state: str = "open") -> List[Dict[str, Any]]:
        """Queries GitHub Issues API to fetch issues for mapping analysis.

        Args:
            repo_fullName: GitHub owner/repo identifier.
            state: Status of issues to retrieve ("open", "closed", "all").

        Returns:
            A list of dictionary records containing issue numbers, titles, bodies, and URLs.
        """
        url = f"https://api.github.com/repos/{repo_fullName}/issues"
        params = {"state": state, "per_page": 100}
        
        try:
            resp = self.session.get(url, params=params)
            resp.raise_for_status()
            issues = resp.json()
            
            result = []
            for issue in issues:
                # GitHub issues endpoint also returns pull requests, filter them out
                if "pull_request" in issue:
                    continue
                result.append({
                    "number": issue.get("number"),
                    "title": issue.get("title"),
                    "body": issue.get("body", ""),
                    "url": issue.get("html_url"),
                    "state": issue.get("state")
                })
            return result
        except Exception as e:
            logger.error(f"Failed to fetch issues for {repo_fullName}: {e}")
            # Fallback to empty list or raise depending on preferences
            return []
