"""Shared utilities for incremental indexing scripts.

Provides helpers for persisting and loading file modification timestamps
used to skip unchanged files during incremental index runs.
"""
import os
import json


def load_timestamps(timestamp_file: str) -> dict:
    """Load file modification timestamps from a JSON file.

    Returns an empty dict if the file does not exist yet.
    """
    if os.path.exists(timestamp_file):
        with open(timestamp_file, 'r') as f:
            return json.load(f)
    return {}


def save_timestamps(timestamps: dict, timestamp_file: str) -> None:
    """Persist file modification timestamps to a JSON file."""
    with open(timestamp_file, 'w') as f:
        json.dump(timestamps, f)


def get_file_mtime(filepath: str) -> float:
    """Return the last modification time of a file as a Unix timestamp."""
    return os.path.getmtime(filepath)
