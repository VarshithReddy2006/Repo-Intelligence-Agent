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

from services.storage_paths import get_cloned_repos_dir

logger = logging.getLogger(__name__)


class InvalidGitHubRepoURLError(ValueError):
    """Raised when the provided repo URL/identifier is not a supported GitHub format."""


class RepositoryNotFoundError(RuntimeError):
    """Raised when the target repository cannot be found (404-like git clone failure)."""


class BranchNotFoundError(ValueError):
    """Raised when the requested branch/ref does not exist in the repository."""


class GitHubConfig:
    token: Optional[str] = None

    @classmethod
    def load_token(cls) -> Optional[str]:
        if cls.token is None:
            from backend.settings import settings

            cls.token = settings.github_token
        return cls.token


class GitHubService:
    """Wrapper class containing helpers to query GitHub repositories or clone them locally."""

    def __init__(self, token: Optional[str] = None) -> None:
        """Initializes the GitHub client with an optional authentication token.

        Args:
            token: GitHub Personal Access Token (PAT).
        """
        self.token = token or GitHubConfig.load_token()
        self.session = requests.Session()
        if self.token:
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        self.session.headers.update({"Accept": "application/vnd.github+json"})

        # Verify request headers
        logger.info(
            "GitHub Authorization header present: %s",
            "Authorization" in self.session.headers,
        )

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
        # Store clones OUTSIDE the project tree so uvicorn --reload (WatchFiles)
        # does not treat clone activity as source-code changes. Configurable via
        # CLONED_REPOS_PATH; defaults to ~/.repo_intelligence/cloned_repos.
        base_dir = str(get_cloned_repos_dir())
        safe_name = repo_fullName.replace("/", "_")
        return os.path.abspath(os.path.join(base_dir, safe_name))

    def clone_repository(self, repo_url: str, branch: Optional[str] = None) -> str:
        """Clones a GitHub repository to a local directory using Git CLI with fallback reliability.

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

        # 1. Determine clone URL for anonymous cloning
        parsed_url = urllib.parse.urlparse(repo_url)
        if parsed_url.scheme:
            public_url = repo_url
        else:
            public_url = f"https://github.com/{repo_fullName}.git"

        # 2. Check if repository is publicly accessible (anonymous check)
        is_public = False
        try:
            cmd_check = ["git", "ls-remote", public_url, "HEAD"]
            res = subprocess.run(cmd_check, capture_output=True, text=True, check=False)
            if res.returncode == 0:
                is_public = True
        except Exception:
            pass

        # 3. Determine actual URL to use
        if is_public:
            clone_url = public_url
            logger.info("Cloning public repository anonymously: %s", repo_fullName)
        elif self.token:
            # Private repo, use token
            if parsed_url.scheme == "https":
                netloc = f"{self.token}@{parsed_url.netloc}"
                clone_url = urllib.parse.urlunparse(parsed_url._replace(netloc=netloc))
            else:
                clone_url = f"https://{self.token}@github.com/{repo_fullName}.git"
            logger.info("Cloning private repository using PAT: %s", repo_fullName)
        else:
            clone_url = public_url
            logger.info(
                "Cloning repository anonymously (no token available): %s", repo_fullName
            )

        # 4. Perform ls-remote connection diagnostics
        try:
            cmd_check = ["git", "ls-remote", clone_url, "HEAD"]
            res = subprocess.run(cmd_check, capture_output=True, text=True, check=False)
            if res.returncode != 0:
                err_stderr = (
                    res.stderr.replace(self.token, "********")
                    if self.token
                    else res.stderr
                )
                err_lower = err_stderr.lower()

                # Check for Network Failure
                if any(
                    kw in err_lower
                    for kw in [
                        "could not resolve host",
                        "temporary failure",
                        "network is unreachable",
                        "timed out",
                    ]
                ):
                    raise RuntimeError(
                        f"Network failure: Check your internet connection. Detail: {err_stderr.strip()}"
                    )
                # Check for Auth / Access Failures
                elif any(
                    kw in err_lower
                    for kw in [
                        "permission denied",
                        "authorization",
                        "terminal",
                        "write access",
                        "403",
                        "401",
                    ]
                ):
                    if not self.token:
                        raise RuntimeError(
                            "Repository private: The repository requires authentication but no GITHUB_TOKEN (PAT) is set in your environment."
                        )
                    else:
                        raise RuntimeError(
                            f"Authentication failure: The provided GITHUB_TOKEN (PAT) is invalid, expired, or does not have read access to {repo_fullName}."
                        )
                # Check for Not Found
                elif any(
                    kw in err_lower
                    for kw in ["not found", "repository not found", "fatal: repository"]
                ):
                    if not is_public and not self.token:
                        raise RuntimeError(
                            f"Repository private: Repository {repo_fullName} was not found anonymously. It might be private; please provide a valid GITHUB_TOKEN (PAT)."
                        )
                    else:
                        raise RepositoryNotFoundError(
                            f"Repository not found: Repository {repo_fullName} does not exist. Detail: {err_stderr.strip()}"
                        )
                else:
                    raise RuntimeError(
                        f"Connection failure: Failed to connect to repository {repo_fullName}. Detail: {err_stderr.strip()}"
                    )
        except Exception as e:
            if isinstance(e, (RepositoryNotFoundError, RuntimeError)):
                raise e
            raise RuntimeError(f"Connection failure: {e}")

        # 5. Resolve Branch name (and auto-discover if requested branch is default 'main' but not present)
        actual_branch = branch
        if branch:
            # Check if requested branch exists
            cmd_check = ["git", "ls-remote", "--heads", clone_url, branch]
            res_check = subprocess.run(
                cmd_check, capture_output=True, text=True, check=False
            )
            branch_exists = res_check.returncode == 0 and bool(res_check.stdout.strip())

            if not branch_exists:
                if branch == "main":
                    # Try to auto-discover default branch
                    try:
                        cmd_sym = ["git", "ls-remote", "--symref", clone_url, "HEAD"]
                        res_sym = subprocess.run(
                            cmd_sym, capture_output=True, text=True, check=False
                        )
                        discovered = None
                        if res_sym.returncode == 0:
                            for line in res_sym.stdout.splitlines():
                                if line.startswith("ref:"):
                                    parts = line.split()
                                    if len(parts) >= 2 and parts[1].startswith(
                                        "refs/heads/"
                                    ):
                                        discovered = parts[1].replace("refs/heads/", "")
                                        break
                        if discovered:
                            actual_branch = discovered
                            logger.info(
                                f"Branch 'main' not found. Auto-discovered default branch: '{actual_branch}'"
                            )
                        else:
                            raise BranchNotFoundError(
                                "Branch 'main' not found, and failed to auto-discover default branch."
                            )
                    except Exception as e:
                        if isinstance(e, BranchNotFoundError):
                            raise e
                        raise BranchNotFoundError(
                            f"Branch 'main' not found for repository {repo_fullName}."
                        )
                else:
                    raise BranchNotFoundError(
                        f"Branch '{branch}' does not exist for repository {repo_fullName}."
                    )

        # 6. Clear target directory
        if os.path.exists(dest_dir):
            try:
                if os.name == "nt":
                    subprocess.run(
                        ["cmd", "/c", "rmdir", "/s", "/q", dest_dir], check=False
                    )
                else:
                    shutil.rmtree(dest_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(
                    f"Failed to completely remove existing directory {dest_dir}: {e}."
                )

        os.makedirs(os.path.dirname(dest_dir), exist_ok=True)

        # 7. Perform Clone
        logger.info(
            f"Cloning repository {repo_fullName} to {dest_dir} (branch={actual_branch})..."
        )
        cmd = ["git", "clone", "--depth", "1", "--single-branch"]
        if actual_branch:
            cmd.extend(["--branch", actual_branch])
        cmd.extend([clone_url, dest_dir])

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            err_msg = (
                result.stderr.replace(self.token, "********")
                if self.token
                else result.stderr
            )
            raise RuntimeError(f"Failed to clone repository: {err_msg}")

        return dest_dir

    def extract_source_files(self, local_path: str) -> List[Dict[str, Any]]:
        """Walks the cloned repository and extracts files, skipping ignored ones.

        Args:
            local_path: Local path to the repository.

        Returns:
            A list of dictionary records containing file paths and contents.
        """
        ignored_names = {
            "node_modules",
            ".git",
            "dist",
            "build",
            ".next",
            "venv",
            ".venv",
            "__pycache__",
            ".tox",
            "coverage",
            "data",
        }
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
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".gif",
                    ".ico",
                    ".pdf",
                    ".zip",
                    ".tar",
                    ".gz",
                    ".mp3",
                    ".mp4",
                    ".woff",
                    ".woff2",
                    ".ttf",
                    ".eot",
                    ".svg",
                    ".pyc",
                    ".db",
                    ".sqlite",
                    ".exe",
                    ".bin",
                    ".dll",
                    ".so",
                    ".dylib",
                    ".pkl",
                    ".h5",
                }:
                    continue

                # Read content as text
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    extracted_files.append(
                        {"path": rel_path.replace(os.sep, "/"), "content": content}
                    )
                except Exception as e:
                    logger.debug(f"Skipping file {rel_path} due to read error: {e}")

        return extracted_files

    def fetch_repository_files(
        self, repo_fullName: str, branch: str = "main"
    ) -> List[Dict[str, Any]]:
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
        ignored_names = {
            "node_modules",
            ".git",
            "dist",
            "build",
            ".next",
            "venv",
            ".venv",
            "__pycache__",
            ".tox",
            "coverage",
            "data",
        }

        for root, dirs, files in os.walk(dest_dir):
            dirs[:] = [d for d in dirs if d not in ignored_names]
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, dest_dir).replace(os.sep, "/")
                if any(part in ignored_names for part in rel_path.split("/")):
                    continue
                size = os.path.getsize(file_path)
                files_meta.append(
                    {
                        "path": rel_path,
                        "type": "blob",
                        "size": size,
                        "url": f"https://github.com/{repo_fullName}/blob/{branch}/{rel_path}",
                    }
                )
        return files_meta

    def fetch_file_content(
        self, repo_fullName: str, file_path: str, ref: str = "main"
    ) -> str:
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
        if not self.token:
            raise RuntimeError("GITHUB_TOKEN is not loaded.")
        url = f"https://api.github.com/repos/{repo_fullName}/contents/{file_path}?ref={ref}"
        try:
            resp = self.session.get(url)
            resp.raise_for_status()
            data = resp.json()
            if "content" in data and data.get("encoding") == "base64":
                import base64

                return base64.b64decode(data["content"]).decode(
                    "utf-8", errors="ignore"
                )
            elif "download_url" in data:
                raw_resp = requests.get(data["download_url"])
                raw_resp.raise_for_status()
                return raw_resp.text
        except Exception as e:
            logger.error(f"Failed to fetch remote file content for {file_path}: {e}")

        raise FileNotFoundError(
            f"File {file_path} not found locally or remotely for repository {repo_fullName}."
        )

    def fetch_issues(
        self, repo_fullName: str, state: str = "open"
    ) -> List[Dict[str, Any]]:
        """Queries GitHub Issues API to fetch issues for mapping analysis.

        Args:
            repo_fullName: GitHub owner/repo identifier.
            state: Status of issues to retrieve ("open", "closed", "all").

        Returns:
            A list of dictionary records containing issue numbers, titles, bodies, and URLs.
        """
        if not self.token:
            raise RuntimeError("GITHUB_TOKEN is not loaded.")
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
                result.append(
                    {
                        "number": issue.get("number"),
                        "title": issue.get("title"),
                        "body": issue.get("body", ""),
                        "url": issue.get("html_url"),
                        "state": issue.get("state"),
                    }
                )
            return result
        except Exception as e:
            logger.error(f"Failed to fetch issues for {repo_fullName}: {e}")
            # Fallback to empty list or raise depending on preferences
            return []

    def fetch_pull_request_metadata(
        self, owner: str, repo: str, pr_number: int
    ) -> Dict[str, Any]:
        """Fetch PR metadata from the GitHub API.

        Args:
            owner: Owner of the repository.
            repo: Name of the repository.
            pr_number: Pull request number.

        Returns:
            Dict containing title, state, html_url, additions, deletions, etc.
        """
        if not self.token:
            raise RuntimeError("GITHUB_TOKEN is not loaded.")
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        try:
            resp = self.session.get(url)
            resp.raise_for_status()
            data = resp.json()
            return {
                "title": data.get("title", ""),
                "state": data.get("state", "open"),
                "html_url": data.get("html_url", ""),
                "additions": data.get("additions", 0),
                "deletions": data.get("deletions", 0),
                "head_sha": data.get("head", {}).get("sha", ""),
            }
        except Exception as e:
            logger.error(
                f"Failed to fetch PR metadata for {owner}/{repo}/pulls/{pr_number}: {e}"
            )
            raise RuntimeError(f"Failed to fetch PR metadata: {e}")

    def fetch_pull_request_files(
        self, owner: str, repo: str, pr_number: int
    ) -> List[Dict[str, Any]]:
        """Fetch files changed in a PR from the GitHub API (handles pagination).

        Args:
            owner: Owner of the repository.
            repo: Name of the repository.
            pr_number: Pull request number.

        Returns:
            List of dict records for each changed file.
        """
        if not self.token:
            raise RuntimeError("GITHUB_TOKEN is not loaded.")
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
        result = []
        page = 1
        per_page = 100

        while True:
            try:
                resp = self.session.get(
                    url, params={"page": page, "per_page": per_page}
                )
                resp.raise_for_status()
                files = resp.json()
                if not files:
                    break
                for f in files:
                    result.append(
                        {
                            "filename": f.get("filename", ""),
                            "status": f.get("status", ""),
                            "additions": f.get("additions", 0),
                            "deletions": f.get("deletions", 0),
                            "changes": f.get("changes", 0),
                        }
                    )
                if len(files) < per_page:
                    break
                page += 1
            except Exception as e:
                logger.error(
                    f"Failed to fetch PR files for {owner}/{repo}/pulls/{pr_number} page {page}: {e}"
                )
                raise RuntimeError(f"Failed to fetch PR files: {e}")

        return result

    def get_rate_limit_info(self) -> Dict[str, Any]:
        """Fetch rate limit information from the GitHub API.

        Returns:
            Dict containing remaining rate limit, reset time, etc.
        """
        if not self.token:
            raise RuntimeError("GITHUB_TOKEN is not loaded.")
        url = "https://api.github.com/rate_limit"
        try:
            resp = self.session.get(url)
            resp.raise_for_status()
            data = resp.json()
            rate = data.get("resources", {}).get("core", {})
            return {
                "limit": rate.get("limit", 0),
                "remaining": rate.get("remaining", 0),
                "reset": rate.get("reset", 0),
            }
        except Exception as e:
            logger.error(f"Failed to fetch rate limit info: {e}")
            return {
                "limit": 0,
                "remaining": 0,
                "reset": 0,
            }
