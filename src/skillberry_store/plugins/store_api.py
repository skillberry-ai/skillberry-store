"""Store API for plugin access to content.

This provides a stable interface that plugins can use to access and modify
store content without depending on internal implementation details.
"""

from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class StoreAPI:
    """API interface for plugins to access store content.
    
    This provides a stable interface that plugins can use without
    depending on internal store implementation details.
    """
    
    def __init__(self, handlers: Dict[str, Any]):
        """Initialize with references to store's object handlers.
        
        Args:
            handlers: Dict with keys 'tools', 'skills', 'snippets' mapping to ObjectHandler instances
        """
        self.tools = handlers.get("tools")
        self.skills = handlers.get("skills")
        self.snippets = handlers.get("snippets")
    
    # Tool operations
    def get_tool(self, uuid: str) -> Optional[Dict[str, Any]]:
        """Get a tool by UUID.
        
        Args:
            uuid: UUID of the tool
            
        Returns:
            Tool dict or None if not found
        """
        if not self.tools:
            return None
        return self.tools.read_dict(uuid)
    
    def list_tools(self, filter_criteria: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """List tools with optional filtering.
        
        Args:
            filter_criteria: Optional dict of field:value pairs to filter by
            
        Returns:
            List of tool dicts matching criteria
        """
        if not self.tools:
            return []
        
        all_tools = list(self.tools.iter_dicts())
        if not filter_criteria:
            return all_tools
        
        # Apply filters
        return [t for t in all_tools if self._matches_filter(t, filter_criteria)]
    
    def update_tool_tags(self, uuid: str, tags: List[str]) -> bool:
        """Add tags to a tool (merges with existing tags).
        
        Args:
            uuid: UUID of the tool
            tags: List of tags to add
            
        Returns:
            True if successful, False if tool not found
        """
        if not self.tools:
            return False
            
        tool = self.get_tool(uuid)
        if not tool:
            return False
        
        existing_tags = set(tool.get("tags", []))
        tool["tags"] = list(existing_tags.union(set(tags)))
        
        try:
            self.tools.write_dict(uuid, tool)
            return True
        except Exception as e:
            logger.error(f"Failed to update tool tags for {uuid}: {e}")
            return False
    
    def update_tool_metadata(self, uuid: str, metadata: Dict[str, Any]) -> bool:
        """Update tool's extra metadata (merges with existing).
        
        Args:
            uuid: UUID of the tool
            metadata: Dict of metadata to add/update
            
        Returns:
            True if successful, False if tool not found
        """
        if not self.tools:
            return False
            
        tool = self.get_tool(uuid)
        if not tool:
            return False
        
        if "extra" not in tool:
            tool["extra"] = {}
        tool["extra"].update(metadata)
        
        try:
            self.tools.write_dict(uuid, tool)
            return True
        except Exception as e:
            logger.error(f"Failed to update tool metadata for {uuid}: {e}")
            return False
    
    # Skill operations
    def get_skill(self, uuid: str) -> Optional[Dict[str, Any]]:
        """Get a skill by UUID.
        
        Args:
            uuid: UUID of the skill
            
        Returns:
            Skill dict or None if not found
        """
        if not self.skills:
            return None
        return self.skills.read_dict(uuid)
    
    def list_skills(self, filter_criteria: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """List skills with optional filtering.
        
        Args:
            filter_criteria: Optional dict of field:value pairs to filter by
            
        Returns:
            List of skill dicts matching criteria
        """
        if not self.skills:
            return []
            
        all_skills = list(self.skills.iter_dicts())
        if not filter_criteria:
            return all_skills
        
        return [s for s in all_skills if self._matches_filter(s, filter_criteria)]
    
    def update_skill_tags(self, uuid: str, tags: List[str]) -> bool:
        """Add tags to a skill (merges with existing tags).
        
        Args:
            uuid: UUID of the skill
            tags: List of tags to add
            
        Returns:
            True if successful, False if skill not found
        """
        if not self.skills:
            return False
            
        skill = self.get_skill(uuid)
        if not skill:
            return False
        
        existing_tags = set(skill.get("tags", []))
        skill["tags"] = list(existing_tags.union(set(tags)))
        
        try:
            self.skills.write_dict(uuid, skill)
            return True
        except Exception as e:
            logger.error(f"Failed to update skill tags for {uuid}: {e}")
            return False
    
    # Snippet operations
    def get_snippet(self, uuid: str) -> Optional[Dict[str, Any]]:
        """Get a snippet by UUID.
        
        Args:
            uuid: UUID of the snippet
            
        Returns:
            Snippet dict or None if not found
        """
        if not self.snippets:
            return None
        return self.snippets.read_dict(uuid)
    
    def list_snippets(self, filter_criteria: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """List snippets with optional filtering.
        
        Args:
            filter_criteria: Optional dict of field:value pairs to filter by
            
        Returns:
            List of snippet dicts matching criteria
        """
        if not self.snippets:
            return []
            
        all_snippets = list(self.snippets.iter_dicts())
        if not filter_criteria:
            return all_snippets
        
        return [s for s in all_snippets if self._matches_filter(s, filter_criteria)]
    
    def create_snippet(self, snippet_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new snippet.
        
        Args:
            snippet_data: Dict with snippet fields (name, content, language, tags, description, etc.)
                         UUID will be auto-generated if not provided.
                         
        Returns:
            Created snippet dict with uuid and timestamps
            
        Raises:
            ValueError: If required fields are missing
            RuntimeError: If snippet creation fails
        """
        if not self.snippets:
            raise RuntimeError("Snippets handler not available")
        
        # Validate required fields
        if "name" not in snippet_data:
            raise ValueError("Snippet name is required")
        if "content" not in snippet_data:
            raise ValueError("Snippet content is required")
        
        # Generate UUID if not provided
        import uuid as uuid_module
        from datetime import datetime, timezone
        
        if "uuid" not in snippet_data or not snippet_data["uuid"]:
            snippet_data["uuid"] = str(uuid_module.uuid4())
        
        # Set timestamps
        current_time = datetime.now(timezone.utc).isoformat()
        snippet_data["created_at"] = current_time
        snippet_data["modified_at"] = current_time
        
        # Set defaults for optional fields
        snippet_data.setdefault("language", "text")
        snippet_data.setdefault("tags", [])
        snippet_data.setdefault("description", "")
        
        try:
            # Check if snippet already exists
            try:
                existing = self.get_snippet(snippet_data["uuid"])
                if existing:
                    raise RuntimeError(f"Snippet with UUID '{snippet_data['uuid']}' already exists")
            except Exception as e:
                # If it's a 404, that's good - snippet doesn't exist yet
                # Any other exception should be re-raised
                if hasattr(e, 'status_code') and e.status_code == 404:
                    pass  # Snippet doesn't exist, continue with creation
                else:
                    raise
            
            # Determine parent for cache
            if snippet_data["name"]:
                snippet_data["parent"] = self.snippets.get_cache_parent_for_head(
                    snippet_data["uuid"], snippet_data["name"]
                )
            
            # Write snippet
            self.snippets.write_dict(snippet_data["uuid"], snippet_data)
            
            # Update cache
            if snippet_data["name"]:
                self.snippets.update_cache(snippet_data["uuid"], new_name=snippet_data["name"])
            
            logger.info(f"Snippet '{snippet_data['name']}' created with UUID: {snippet_data['uuid']}")
            return snippet_data
            
        except Exception as e:
            logger.error(f"Failed to create snippet: {e}")
            raise RuntimeError(f"Failed to create snippet: {str(e)}")
    
    def update_snippet_tags(self, uuid: str, tags: List[str]) -> bool:
        """Add tags to a snippet (merges with existing tags).
        
        Args:
            uuid: UUID of the snippet
            tags: List of tags to add
            
        Returns:
            True if successful, False if snippet not found
        """
        if not self.snippets:
            return False
            
        snippet = self.get_snippet(uuid)
        if not snippet:
            return False
        
        existing_tags = set(snippet.get("tags", []))
        snippet["tags"] = list(existing_tags.union(set(tags)))
        
        try:
            self.snippets.write_dict(uuid, snippet)
            return True
        except Exception as e:
            logger.error(f"Failed to update snippet tags for {uuid}: {e}")
            return False
    
    def _matches_filter(self, item: Dict[str, Any], filter_criteria: Dict) -> bool:
        """Check if item matches filter criteria.
        
        Args:
            item: Dict to check
            filter_criteria: Dict of field:value pairs that must match
            
        Returns:
            True if all criteria match, False otherwise
        """
        for key, value in filter_criteria.items():
            if key not in item:
                return False
            if item[key] != value:
                return False
        return True

# Made with Bob
