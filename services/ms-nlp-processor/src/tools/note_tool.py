"""
Base class for note-taking tools.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import os
from github import Github
from langchain_core.tools import tool

class BaseNoteTool(ABC):
    """Abstract base class for note-taking tools."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def search_notes(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Search for notes based on a query."""
        pass

    @abstractmethod
    def read_note(self, note_id: str, **kwargs) -> str:
        """Read the content of a specific note."""
        pass

class ObsidianGitHubTool(BaseNoteTool):
    """Tool to interact with Obsidian notes stored in a GitHub repository."""

    def __init__(self, name: str = "ObsidianGitHubTool", description: str = "Searches and reads notes from an Obsidian vault in GitHub."):
        super().__init__(name, description)

    @staticmethod
    def validate_configuration(state: Dict[str, Any]):

        state.get("vault_path")

        github_config = state.get("github_config")

        if not github_config:
            raise ValueError("GitHub config not found in state.")


    @staticmethod
    def _get_repo_from_state(state: Dict[str, Any]):
        github_config = state.get("github_config")
        if not github_config:
            raise ValueError("GitHub config not found in state.")

        token = github_config.get("github_token")
        repo_name = github_config.get("repo_name")

        if not token or not repo_name:
            raise ValueError("GitHub token or repo name missing from config.")

        github = Github(token)
        return github.get_repo(repo_name)
    
    @tool
    async def search_notes(state: Dict[str, Any], query: str, **kwargs) -> List[Dict[str, Any]]:
        """Search for my obsidian notes in the GitHub repository."""
        try:
            repo = ObsidianGitHubTool._get_repo_from_state(state)
            # Placeholder for search logic using repo object
            print(f"Searching in {repo.full_name} for notes with query: {query}")
            return []
        except Exception as e:
            return f"Error searching notes: {e}"

    @tool
    async def read_note(state: Dict[str, Any], note_id: str, **kwargs) -> str:
        """Read a specific obsidian note from the GitHub repository."""
        try:
            repo = ObsidianGitHubTool._get_repo_from_state(state)
            file_content = repo.get_contents(note_id)
            return file_content.decoded_content.decode('utf-8')
        except Exception as e:
            return f"Error reading note: {e}"
