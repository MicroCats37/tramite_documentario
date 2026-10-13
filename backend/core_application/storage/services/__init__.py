"""
core_application.storage.services — shared storage service abstractions.

This package provides:
- abstract_storage.py: AbstractStorageService (port interface),
  LocalStorageService (Django default storage), and SaaaStorageService
  (uploads to SAAA and stores pointer in FileField).
"""
from core_application.storage.services.abstract_storage import (
    AbstractStorageService,
    LocalStorageService,
    SaaaStorageService,
)

__all__ = [
    "AbstractStorageService",
    "LocalStorageService",
    "SaaaStorageService",
]
