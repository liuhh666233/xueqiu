"""Scraper configuration loaded from YAML file and/or environment variables."""

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


DEFAULT_CONFIG_PATH = Path("config.yaml")
DEFAULT_DATA_DIR = Path("data/articles")
DEFAULT_USER_ID = 2426670165
DEFAULT_REQUEST_DELAY = 3.0
DEFAULT_PAGE_SIZE = 10


class ScraperConfig(BaseModel):
    """Configuration for the Xueqiu scraper.

    Values are loaded from a YAML file and can be overridden by
    environment variables or CLI arguments.
    """

    user_id: int = DEFAULT_USER_ID
    cookie: str = ""
    data_dir: Path = DEFAULT_DATA_DIR
    request_delay: float = DEFAULT_REQUEST_DELAY
    page_size: int = DEFAULT_PAGE_SIZE
    max_pages: int = Field(
        default=0,
        description="Maximum pages to fetch. 0 means all pages.",
    )


def load_config(
    config_path: Path | None = None,
    cookie: str | None = None,
) -> ScraperConfig:
    """Load configuration from YAML file, env vars, and explicit overrides.

    Args:
        config_path: Path to YAML config file. Falls back to ``config.yaml``
            in the current directory if it exists.
        cookie: Explicit cookie value, takes highest priority.

    Returns:
        Merged ScraperConfig instance.
    """
    values: dict = {}

    # 1. Load from YAML file
    path = config_path or DEFAULT_CONFIG_PATH
    if path.exists():
        with open(path) as f:
            yaml_data = yaml.safe_load(f)
        if isinstance(yaml_data, dict):
            values.update(yaml_data)

    # 2. Override with environment variables
    env_cookie = os.environ.get("XUEQIU_COOKIE")
    if env_cookie:
        values["cookie"] = env_cookie

    env_user_id = os.environ.get("XUEQIU_USER_ID")
    if env_user_id:
        values["user_id"] = int(env_user_id)

    env_data_dir = os.environ.get("XUEQIU_DATA_DIR")
    if env_data_dir:
        values["data_dir"] = env_data_dir

    # 3. Override with explicit arguments
    if cookie:
        values["cookie"] = cookie

    return ScraperConfig(**values)
