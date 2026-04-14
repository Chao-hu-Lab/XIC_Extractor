import importlib
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

EXPECTED_THERMO_DLLS = (
    "ThermoFisher.CommonCore.Data.dll",
    "ThermoFisher.CommonCore.RawFileReader.dll",
)

_ASSEMBLIES_LOADED = False


class RawReaderError(Exception):
    """Raised when Thermo raw reader setup or file opening fails."""


@dataclass(frozen=True)
class Ms2Scan:
    scan_number: int
    precursor_mz: float
    masses: np.ndarray
    intensities: np.ndarray
    base_peak: float


@dataclass(frozen=True)
class Ms2ScanEvent:
    scan: Ms2Scan | None
    parse_error: str | None
    scan_number: int


@dataclass(frozen=True)
class _ThermoApi:
    raw_file_reader_adapter: Any
    device_ms: Any
    mass_range_factory: Callable[[float, float], Any]
    trace_settings_factory: Callable[[], Any]
    mass_range_trace_type: Any
    ms2_order: Any


class RawFileHandle:
    def __init__(self, raw_file: Any, thermo: _ThermoApi) -> None:
        self._raw_file = raw_file
        self._thermo = thermo

    def __enter__(self) -> "RawFileHandle":
        return self

    def __exit__(self, *_args: object) -> None:
        self._raw_file.Dispose()

    def extract_xic(
        self, mz: float, rt_min: float, rt_max: float, ppm_tol: float
    ) -> tuple[np.ndarray, np.ndarray]:
        start_scan = self._raw_file.ScanNumberFromRetentionTime(rt_min)
        end_scan = self._raw_file.ScanNumberFromRetentionTime(rt_max)
        settings = self._build_chromatogram_settings(mz, ppm_tol)
        data = self._raw_file.GetChromatogramData([settings], start_scan, end_scan)
        positions = _first_or_empty(data.PositionsArray)
        intensities = _first_or_empty(data.IntensitiesArray)
        if len(intensities) == 0:
            return np.array([], dtype=float), np.array([], dtype=float)
        return np.asarray(positions, dtype=float), np.asarray(intensities, dtype=float)

    def iter_ms2_scans(self, rt_min: float, rt_max: float) -> Iterator[Ms2ScanEvent]:
        start_scan = self._raw_file.ScanNumberFromRetentionTime(rt_min)
        end_scan = self._raw_file.ScanNumberFromRetentionTime(rt_max)
        for scan_number in range(start_scan, end_scan + 1):
            try:
                filter_obj = self._raw_file.GetFilterForScanNumber(scan_number)
                if getattr(filter_obj, "MSOrder", None) != self._thermo.ms2_order:
                    continue
                precursor_mz = _extract_precursor_mz(filter_obj)
                scan_data = self._raw_file.GetSimplifiedScan(scan_number)
                masses = np.asarray(getattr(scan_data, "Masses", []), dtype=float)
                intensities = np.asarray(getattr(scan_data, "Intensities", []), dtype=float)
                base_peak = float(np.max(intensities)) if len(intensities) else 0.0
                yield Ms2ScanEvent(
                    scan=Ms2Scan(
                        scan_number=scan_number,
                        precursor_mz=precursor_mz,
                        masses=masses,
                        intensities=intensities,
                        base_peak=base_peak,
                    ),
                    parse_error=None,
                    scan_number=scan_number,
                )
            except Exception as exc:
                yield Ms2ScanEvent(
                    scan=None,
                    parse_error=str(exc),
                    scan_number=scan_number,
                )

    def _build_chromatogram_settings(self, mz: float, ppm_tol: float) -> Any:
        tolerance = mz * ppm_tol / 1e6
        settings = self._thermo.trace_settings_factory()
        settings.MassRanges = [
            self._thermo.mass_range_factory(mz - tolerance, mz + tolerance)
        ]
        settings.Filter = "ms"
        if hasattr(settings, "TraceType"):
            settings.TraceType = self._thermo.mass_range_trace_type
        return settings


def open_raw(
    path: Path,
    dll_dir: Path,
    *,
    _import_module: Callable[[str], Any] = importlib.import_module,
    _thermo: _ThermoApi | None = None,
) -> RawFileHandle:
    errors = preflight_raw_reader(dll_dir, import_module_func=_import_module)
    if errors:
        raise RawReaderError(" ".join(errors))

    resolved_dll_dir = dll_dir.resolve()
    try:
        _ensure_assemblies_loaded(resolved_dll_dir, _import_module)
        thermo = _thermo or _load_thermo_api(_import_module)
        raw_file = thermo.raw_file_reader_adapter.FileFactory(str(path))
        raw_file.SelectInstrument(thermo.device_ms, 1)
    except Exception as exc:
        raise RawReaderError(f"Failed to load Thermo DLL or open raw file: {exc}") from exc
    return RawFileHandle(raw_file, thermo)


def preflight_raw_reader(
    dll_dir: Path,
    *,
    import_module_func: Callable[[str], Any] = importlib.import_module,
) -> list[str]:
    errors: list[str] = []
    try:
        pythonnet = import_module_func("pythonnet")
        _check_dotnet_runtime(pythonnet)
    except ImportError:
        errors.append(
            "pythonnet is not installed; Install project dependencies with `uv sync`."
        )
    except Exception as exc:
        errors.append(f".NET runtime is not available ({exc}); Install .NET 6+ runtime.")

    try:
        resolved = dll_dir.resolve(strict=True)
    except OSError:
        errors.append(
            f"Xcalibur DLL directory was not found at `{dll_dir}`; open Settings and correct DLL directory."
        )
        return errors

    for dll_name in EXPECTED_THERMO_DLLS:
        dll_path = resolved / dll_name
        if not dll_path.is_file():
            errors.append(
                f"Xcalibur DLL `{dll_name}` was not found in `{resolved}`; open Settings and correct DLL directory."
            )
    return errors


def reset_reader_state() -> None:
    global _ASSEMBLIES_LOADED
    _ASSEMBLIES_LOADED = False


def _check_dotnet_runtime(pythonnet: Any) -> None:
    get_runtime_info = getattr(pythonnet, "get_runtime_info", None)
    if callable(get_runtime_info):
        get_runtime_info()


def _ensure_assemblies_loaded(
    dll_dir: Path, import_module_func: Callable[[str], Any]
) -> None:
    global _ASSEMBLIES_LOADED
    if _ASSEMBLIES_LOADED:
        return
    clr = import_module_func("clr")
    for dll_name in EXPECTED_THERMO_DLLS:
        dll_path = dll_dir / dll_name
        try:
            clr.AddReference(str(dll_path))
        except Exception as exc:
            raise RawReaderError(f"Failed to load Thermo DLL `{dll_path}`: {exc}") from exc
    _ASSEMBLIES_LOADED = True


def _load_thermo_api(import_module_func: Callable[[str], Any]) -> _ThermoApi:
    raw_module = import_module_func("ThermoFisher.CommonCore.RawFileReader")
    business = import_module_func("ThermoFisher.CommonCore.Data.Business")
    filter_enums = import_module_func("ThermoFisher.CommonCore.Data.FilterEnums")
    return _ThermoApi(
        raw_file_reader_adapter=raw_module.RawFileReaderAdapter,
        device_ms=business.Device.MS,
        mass_range_factory=business.Range,
        trace_settings_factory=business.ChromatogramTraceSettings,
        mass_range_trace_type=business.TraceType.MassRange,
        ms2_order=filter_enums.MSOrderType.Ms2,
    )


def _first_or_empty(values: Any) -> Any:
    if values is None or len(values) == 0:
        return []
    return values[0]


def _extract_precursor_mz(filter_obj: Any) -> float:
    reactions = getattr(getattr(filter_obj, "Filter", SimpleNamespace()), "Reactions", [])
    if reactions is None or len(reactions) == 0:
        raise RawReaderError("MS2 filter has no precursor reaction")
    return float(reactions[0].PrecursorMass)
