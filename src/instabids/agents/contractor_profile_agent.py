"""Agent façade that other agents call when they need profile info."""
from __future__ import annotations
from typing import Dict, Any, Optional

# Attempt to import the repo, assuming it's now available
try:
    from instabids.data import contractor_repo as repo
except ImportError:
    print("Warning: Could not import contractor_repo.")
    # Define a dummy repo or raise error if needed for structure
    class DummyRepo:
        def create_profile(self, row): return {**row, 'id': 'dummy_id'}
        def get_profile(self, user_id): return {'user_id': user_id, 'display_name': 'Dummy'} if user_id else None
        def update_profile(self, user_id, updates): return {'user_id': user_id, **updates}
        def delete_profile(self, user_id): pass
    repo = DummyRepo()

class ContractorProfileAgent:
    """Lightweight wrapper – no LLM, just data orchestration."""

    def create(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a new contractor profile.

        Args:
            user_id: The UUID of the user associated with this profile.
            payload: A dictionary containing profile data (e.g., display_name, trade).

        Returns:
            The created profile data dictionary.
        """
        # Ensure user_id is included in the row data passed to the repo
        row = {"user_id": user_id, **payload}
        # Consider adding validation here before calling repo
        return repo.create_profile(row)

    def get(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a contractor profile by user_id.

        Args:
            user_id: The UUID of the user whose profile is being fetched.

        Returns:
            The profile data dictionary, or None if not found.
        """
        return repo.get_profile(user_id)

    def update(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Updates an existing contractor profile.

        Args:
            user_id: The UUID of the user whose profile is being updated.
            updates: A dictionary containing the fields to update.

        Returns:
            The updated profile data dictionary.
        """
        # Consider adding validation for update payload here
        return repo.update_profile(user_id, updates)

    def delete(self, user_id: str) -> None:
        """Deletes a contractor profile.

        Args:
            user_id: The UUID of the user whose profile is being deleted.
        """
        repo.delete_profile(user_id)
