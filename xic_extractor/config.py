"""Compatibility facade for configuration loading."""

from xic_extractor.configuration.hashing import compute_config_hash
from xic_extractor.configuration.loader import load_config
from xic_extractor.configuration.models import ConfigError, ExtractionConfig, Target
from xic_extractor.configuration.settings import migrate_settings_dict

__all__ = [
    "ConfigError",
    "ExtractionConfig",
    "Target",
    "compute_config_hash",
    "load_config",
    "migrate_settings_dict",
]
