import json
import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)

UNKNOWN_BUILD_INFO = {"version": "unknown", "branch": "unknown", "commit": "unknown"}


@lru_cache(maxsize=1)
def user_agent() -> str:
    """How this application identifies itself to the endpoints it calls."""
    return f"ethereum-head-watcher/{get_build_info().get('version', 'unknown')}"


def get_build_info() -> dict:
    path = "./build-info.json"
    if os.path.exists(path):
        with open(path, "r") as f:
            try:
                build_info = json.load(f)
            except json.JSONDecodeError as error:
                logger.warning({"msg": "Failed to load build info file", "error": error})
                return UNKNOWN_BUILD_INFO
        return build_info
    logger.info({"msg": "Build info file not found"})
    return UNKNOWN_BUILD_INFO
