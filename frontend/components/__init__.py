# frontend/components/__init__.py
"""
Frontend components for the NL-to-SQL system
"""

from .sql_interface import SQLInterface
from .admin_interface import AdminInterface

__all__ = ['SQLInterface', 'AdminInterface']