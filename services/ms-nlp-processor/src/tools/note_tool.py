"""
Base class for note-taking tools.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any

from github import Github, GithubException

from database.database import get_db
from database.crud import get_service_integration
from agents.base_agent import AgentState

from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig


class BaseNoteTool(ABC):
    """Abstract base class for note-taking tools."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

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
    def _extract_repo_full_name(notes_path: str) -> str:
        """Normalize the notes_path into the <owner>/<repo> form expected by PyGithub."""
        if not notes_path:
            return ""

        repo_full_name = notes_path.strip()
        if repo_full_name.endswith(".git"):
            repo_full_name = repo_full_name[:-4]

        prefix = "https://github.com/"
        if repo_full_name.startswith(prefix):
            repo_full_name = repo_full_name[len(prefix):]

        return repo_full_name.strip("/")
    
    @staticmethod
    def _get_repo_from_state(state: Dict[str, Any]):
        notes_path = state.get("notes_path")
        user_email = state.get("user_email")

        repo_full_name = ObsidianGitHubTool._extract_repo_full_name(notes_path or "")
        if not repo_full_name:
            raise ValueError("Update your configuration to select a valid GitHub notes repository.")

        if not user_email:
            raise ValueError("Authenticated user email not available to retrieve GitHub integration.")

        db = next(get_db())
        try:
            integration = get_service_integration(db, user_email, "github")
            if not integration or not integration.access_token:
                raise ValueError("GitHub integration not configured. Please connect your GitHub account.")

            github_client = Github(integration.access_token)
            return github_client.get_repo(repo_full_name)
        finally:
            db.close()
    
    @staticmethod
    def _normalize_note_path(note_id: str) -> str:
        if not note_id:
            raise ValueError("Note path is required.")
        normalized = note_id.strip()
        if not normalized:
            raise ValueError("Note path is required.")
        if not normalized.endswith(".md"):
            normalized += ".md"
        return normalized

    @tool
    async def search_notes(config: RunnableConfig, state: AgentState, query: str) -> List[Dict[str, Any]]:
        """Search for my obsidian notes in the GitHub repository."""
        try:
            repo = ObsidianGitHubTool._get_repo_from_state(state)
            # Placeholder for search logic using repo object
            print(f"Searching in {repo.full_name} for notes with query: {query}")
            return []
        except Exception as e:
            return f"Error searching notes: {e}"

    @tool
    async def read_note(note_id: str, tool_runtime: ToolRuntime) -> str:
        """Read a specific obsidian note from the GitHub repository.
        
           Args: 
            - note_id: The ID of the note to read.
            - tool_runtime: ToolsRuntime

           Returns: The content of the note or an error message.
        """
        try:
            if not note_id:
                return "Note ID is required."

            state = getattr(tool_runtime, "state", {}) or {}
            repo = ObsidianGitHubTool._get_repo_from_state(state)
            note_path = ObsidianGitHubTool._normalize_note_path(note_id)

            file_content = repo.get_contents(note_path)
            return file_content.decoded_content.decode('utf-8')
        except Exception as e:
            return f"Error reading note: {e}"

    @tool
    async def create_or_update_note(
        note_path: str,
        content: str,
        tool_runtime: ToolRuntime,
        commit_message: str = "Update Obsidian note by Samantha",
    ) -> str:
        """
        Create or update an Obsidian note. 
        
        Args:
            - note_path: The path to the note.
            - content: The content of the note.
            - tool_runtime: ToolsRuntime
            - commit_message: The commit message for the update.
        
        Returns:
            A message indicating success or failure.
        """
        try:
            
            if content is None:
                return "Content for the note is required."

            state = getattr(tool_runtime, "state", {}) or {}
            repo = ObsidianGitHubTool._get_repo_from_state(state)

            normalized_path = ObsidianGitHubTool._normalize_note_path(note_path)
            branch = state.get("notes_branch")
            target_branch = branch or getattr(repo, "default_branch", None)

            existing_file = None
            try:
                existing_file = repo.get_contents(normalized_path, ref=target_branch)
            except GithubException as gh_exc:
                if gh_exc.status != 404:
                    return f"Error fetching note: {gh_exc}"

            if existing_file:
                repo.update_file(
                    normalized_path,
                    commit_message,
                    content,
                    existing_file.sha,
                    branch=target_branch,
                )
                return f"Note '{normalized_path}' updated successfully."

            repo.create_file(
                normalized_path,
                commit_message,
                content,
                branch=target_branch,
            )
            return f"Note '{normalized_path}' created successfully."
        except Exception as e:
            return f"Error writing note: {e}"
