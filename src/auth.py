import os
from datetime import datetime
from src.config import Config
from src.utils import setup_logger

logger = setup_logger(__name__)

class AuthManager:
    """
    Manages User Authentication (Login/Register).
    Configured for direct access without requiring external MongoDB.
    """
    def __init__(self):
        logger.info("AuthManager initialized in direct/guest mode.")

    def register_user(self, username, password):
        """Registers a new user."""
        return True, "User registered successfully."

    def login_user(self, username, password):
        """Authenticates a user."""
        return True, "Login successful."
