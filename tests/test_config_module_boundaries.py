import inspect

from xic_extractor import config
from xic_extractor.config import (
    ConfigError,
    ExtractionConfig,
    Target,
    compute_config_hash,
    load_config,
    migrate_settings_dict,
)


def test_config_facade_keeps_public_imports() -> None:
    assert config.ConfigError is ConfigError
    assert config.ExtractionConfig is ExtractionConfig
    assert config.Target is Target
    assert config.compute_config_hash is compute_config_hash
    assert config.load_config is load_config
    assert config.migrate_settings_dict is migrate_settings_dict


def test_config_module_is_compatibility_facade() -> None:
    source = inspect.getsource(config)

    assert "csv.DictReader" not in source
    assert "_parse_settings_values" not in source
    assert "_read_targets" not in source
    assert "CANONICAL_SETTINGS_DEFAULTS" not in source
