from pathlib import Path


def test_backend_domain_directories_exist() -> None:
    app_dir = Path(__file__).resolve().parents[1] / "app"
    for name in ["api", "core", "db", "models", "schemas", "services", "workers", "scoring", "parsers"]:
        assert (app_dir / name).exists()

