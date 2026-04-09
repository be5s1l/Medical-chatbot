import sys
from pathlib import Path


def pytest_configure():
    """
    Ensure `medical_chatbot/` is on sys.path so imports like `from src...` work.
    Repo layout: repo_root/medical_chatbot/src/...
    """
    project_root = Path(__file__).resolve().parents[1]  # .../medical_chatbot
    sys.path.insert(0, str(project_root))

