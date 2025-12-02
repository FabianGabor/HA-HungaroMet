"""Pytest configuration for the HungaroMet integration tests."""

import importlib.util
import sys
import types
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "custom_components.hungaromet"


def _ensure_namespace_package() -> None:
    if "custom_components" not in sys.modules:
        custom_components = types.ModuleType("custom_components")
        custom_components.__path__ = []  # type: ignore[attr-defined]
        sys.modules["custom_components"] = custom_components
    else:
        custom_components = sys.modules["custom_components"]

    if PACKAGE_NAME not in sys.modules:
        hungaromet_pkg = types.ModuleType(PACKAGE_NAME)
        hungaromet_pkg.__path__ = [str(PROJECT_ROOT)]  # type: ignore[attr-defined]
        sys.modules[PACKAGE_NAME] = hungaromet_pkg
        setattr(custom_components, "hungaromet", hungaromet_pkg)
    else:
        setattr(custom_components, "hungaromet", sys.modules[PACKAGE_NAME])


def _load_module(module: str) -> None:
    full_name = f"{PACKAGE_NAME}.{module}"
    if full_name in sys.modules:
        return

    spec = importlib.util.spec_from_file_location(
        full_name, PROJECT_ROOT / f"{module}.py"
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module {full_name}")

    module_obj = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module_obj
    setattr(sys.modules[PACKAGE_NAME], module, module_obj)
    spec.loader.exec_module(module_obj)


def pytest_configure() -> None:
    _ensure_namespace_package()
    for module in (
        "__init__",
        "const",
        "weather_data",
        "daily_sensor",
        "hourly_sensor",
        "ten_minutes_sensor",
        "radar_gif_image",
        "radar_gif_creator",
        "station_info_sensor",
        "image",
    ):
        _load_module(module)
