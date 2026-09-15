from src.config import PROJECT_PATHS


def test_project_paths_root_exists():
    assert PROJECT_PATHS.root.exists()
