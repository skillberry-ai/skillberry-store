"""Common search filtering utilities for API endpoints."""

import logging
from typing import List, Dict, Any

from skillberry_store.modules.dictionary_checker import DictionaryChecker
from skillberry_store.modules.lifecycle import LifecycleState, LifecycleManager

logger = logging.getLogger(__name__)


def apply_search_filters(
    entities: List[Dict[str, Any]],
    manifest_filter: str = ".",
    lifecycle_state: LifecycleState = LifecycleState.ANY,
) -> List[Dict[str, Any]]:
    """Apply manifest property and lifecycle state filters to a list of entities.
    
    This function filters entities based on:
    1. Lifecycle state - filters by the entity's lifecycle state
    2. Manifest properties - filters using DictionaryChecker for flexible key-value matching
    
    Args:
        entities: List of entity dictionaries to filter.
        manifest_filter: Manifest properties to filter (e.g., "tags:python", "state:approved").
                        Default "." matches all entities.
        lifecycle_state: State to filter by. Default LifecycleState.ANY matches all states.
    
    Returns:
        List of filtered entity dictionaries.
    
    Example:
        >>> entities = [
        ...     {"name": "tool1", "state": "approved", "tags": ["python"]},
        ...     {"name": "tool2", "state": "new", "tags": ["javascript"]}
        ... ]
        >>> filtered = apply_search_filters(
        ...     entities,
        ...     manifest_filter="tags:python",
        ...     lifecycle_state=LifecycleState.APPROVED
        ... )
        >>> # Returns only tool1
    """
    filtered_entities = entities
    
    # Filter by lifecycle state if specified
    if lifecycle_state is not LifecycleState.ANY:
        matched_entities = []
        for entity in filtered_entities:
            life_cycle_manager = LifecycleManager(entity)
            if life_cycle_manager.get_state() != lifecycle_state:
                continue
            matched_entities.append(entity)
        filtered_entities = matched_entities
        logger.debug(f"After lifecycle filter ({lifecycle_state}): {len(filtered_entities)} entities")
    
    # Filter by manifest properties if specified
    if manifest_filter != "" and manifest_filter != ".":
        matched_entities = []
        for entity in filtered_entities:
            dictionary_checker = DictionaryChecker(entity)
            if not dictionary_checker.check_key_value_exists(manifest_filter):
                continue
            matched_entities.append(entity)
        filtered_entities = matched_entities
        logger.debug(f"After manifest filter ({manifest_filter}): {len(filtered_entities)} entities")
    
    return filtered_entities