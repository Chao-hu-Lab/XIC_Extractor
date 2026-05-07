from PyQt6.QtWidgets import QDoubleSpinBox, QSpinBox

from xic_extractor.settings_schema import CANONICAL_SETTINGS_DEFAULTS


def _int_value(settings: dict[str, str], key: str) -> int:
    try:
        return int(settings.get(key, CANONICAL_SETTINGS_DEFAULTS[key]))
    except ValueError:
        return int(CANONICAL_SETTINGS_DEFAULTS[key])


def _float_value(settings: dict[str, str], key: str) -> float:
    try:
        return float(settings.get(key, CANONICAL_SETTINGS_DEFAULTS[key]))
    except ValueError:
        return float(CANONICAL_SETTINGS_DEFAULTS[key])


def _bool_value(settings: dict[str, str], key: str) -> bool:
    return settings.get(key, CANONICAL_SETTINGS_DEFAULTS[key]).lower() == "true"


def _invalid_parallel_mode(value: str) -> str | None:
    return None if value in {"serial", "process"} else value


def _invalid_parallel_workers(value: str) -> str | None:
    try:
        return None if int(value) >= 1 else value
    except ValueError:
        return value


def _int_setting_text(
    settings: dict[str, str],
    key: str,
    spin: QSpinBox,
) -> str:
    original = settings.get(key, CANONICAL_SETTINGS_DEFAULTS[key])
    try:
        if spin.value() == int(original):
            return original
    except ValueError:
        pass
    return str(spin.value())


def _float_setting_text(
    settings: dict[str, str],
    key: str,
    spin: QDoubleSpinBox,
) -> str:
    original = settings.get(key, CANONICAL_SETTINGS_DEFAULTS[key])
    try:
        tolerance = 10 ** -spin.decimals()
        if abs(spin.value() - float(original)) <= tolerance:
            return original
    except ValueError:
        pass
    return f"{spin.value():g}"
