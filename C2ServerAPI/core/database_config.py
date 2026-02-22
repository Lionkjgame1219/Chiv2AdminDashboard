"""Database configuration and initialization.

This module handles the database connection setup and session management
for the sanction tracking system. Supports both local SQLite and remote
databases (PostgreSQL, MySQL) for centralized multi-user environments.
"""

import os
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool, StaticPool
from .database_models import Base

# Configuration file for database connection settings
DB_CONFIG_FILE = "database_config.json"

# Default configuration for local SQLite (fallback)
DEFAULT_CONFIG = {
    "type": "sqlite",
    "path": "sanctions.db"
}


class DatabaseConfig:
    """Configuration class for database connection and session management.

    Supports multiple database backends:
    - SQLite (local, for testing/development)
    - PostgreSQL (recommended for production/multi-user)
    - MySQL/MariaDB (alternative for production)
    """

    def __init__(self, config=None, echo=False):
        """Initialize the database configuration.

        Args:
            config: Database configuration dictionary or None to load from file
            echo: Whether to echo SQL statements to console (default: False)
        """
        self.config = config or self._load_config()
        self.echo = echo
        self.engine = None
        self.session_factory = None
        self.Session = None

    def _load_config(self):
        """Load database configuration from file or use defaults.

        Returns:
            dict: Database configuration
        """
        if os.path.exists(DB_CONFIG_FILE):
            try:
                with open(DB_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    print(f"[DATABASE] Loaded configuration from {DB_CONFIG_FILE}")
                    return config
            except Exception as e:
                print(f"[DATABASE] Error loading config file: {e}, using defaults")

        return DEFAULT_CONFIG.copy()

    def _build_connection_url(self):
        """Build SQLAlchemy connection URL from configuration.

        Returns:
            str: Database connection URL
        """
        db_type = self.config.get('type', 'sqlite').lower()

        if db_type == 'sqlite':
            # Local SQLite database
            db_path = self.config.get('path', 'sanctions.db')
            return f"sqlite:///{db_path}"

        elif db_type == 'postgresql':
            # Remote PostgreSQL database
            host = self.config.get('host', 'localhost')
            port = self.config.get('port', 5432)
            database = self.config.get('database', 'sanctions')
            username = self.config.get('username', 'postgres')
            password = self.config.get('password', '')

            return f"postgresql://{username}:{password}@{host}:{port}/{database}"

        elif db_type in ['mysql', 'mariadb']:
            # Remote MySQL/MariaDB database
            host = self.config.get('host', 'localhost')
            port = self.config.get('port', 3306)
            database = self.config.get('database', 'sanctions')
            username = self.config.get('username', 'root')
            password = self.config.get('password', '')

            return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"

        else:
            raise ValueError(f"Unsupported database type: {db_type}")

    def initialize(self):
        """Initialize the database engine and create tables if they don't exist.

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            db_url = self._build_connection_url()
            db_type = self.config.get('type', 'sqlite').lower()

            # Configure engine based on database type
            if db_type == 'sqlite':
                # SQLite-specific configuration
                self.engine = create_engine(
                    db_url,
                    echo=self.echo,
                    connect_args={'check_same_thread': False},
                    poolclass=StaticPool
                )
            else:
                # Remote database configuration with connection pooling
                pool_size = self.config.get('pool_size', 5)
                max_overflow = self.config.get('max_overflow', 10)
                pool_timeout = self.config.get('pool_timeout', 30)

                self.engine = create_engine(
                    db_url,
                    echo=self.echo,
                    poolclass=QueuePool,
                    pool_size=pool_size,
                    max_overflow=max_overflow,
                    pool_timeout=pool_timeout,
                    pool_pre_ping=True  # Verify connections before using
                )

            # Create all tables defined in Base metadata
            Base.metadata.create_all(self.engine)

            # Create session factory
            self.session_factory = sessionmaker(bind=self.engine)

            # Create scoped session for thread-safe access
            self.Session = scoped_session(self.session_factory)

            print(f"[DATABASE] Successfully initialized {db_type} database")
            return True

        except Exception as e:
            print(f"[DATABASE] Error initializing database: {e}")
            return False

    def get_session(self):
        """Get a new database session.

        Returns:
            Session: SQLAlchemy session object
        """
        if self.Session is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self.Session()

    def test_connection(self):
        """Test the database connection.

        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            session = self.get_session()
            session.execute("SELECT 1")
            session.close()
            print("[DATABASE] Connection test successful")
            return True
        except Exception as e:
            print(f"[DATABASE] Connection test failed: {e}")
            return False

    def close(self):
        """Close the database connection and clean up resources."""
        if self.Session:
            self.Session.remove()
        if self.engine:
            self.engine.dispose()
        print("[DATABASE] Database connection closed")


# Global database configuration instance
_db_config = None


def get_database_config(config=None, echo=False):
    """Get or create the global database configuration instance.

    Args:
        config: Database configuration dictionary or None to load from file
        echo: Whether to echo SQL statements to console (default: False)

    Returns:
        DatabaseConfig: The global database configuration instance
    """
    global _db_config

    if _db_config is None:
        _db_config = DatabaseConfig(config=config, echo=echo)
        _db_config.initialize()

    return _db_config


def get_session():
    """Get a new database session from the global configuration.

    Returns:
        Session: SQLAlchemy session object
    """
    config = get_database_config()
    return config.get_session()


def close_database():
    """Close the global database connection."""
    global _db_config

    if _db_config:
        _db_config.close()
        _db_config = None


def save_config(config):
    """Save database configuration to file.

    Args:
        config: Database configuration dictionary

    Returns:
        bool: True if save was successful, False otherwise
    """
    try:
        with open(DB_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        print(f"[DATABASE] Configuration saved to {DB_CONFIG_FILE}")
        return True
    except Exception as e:
        print(f"[DATABASE] Error saving configuration: {e}")
        return False

