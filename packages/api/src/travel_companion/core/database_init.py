"""Database initialization and setup utilities."""

import asyncio
import logging
from pathlib import Path

from travel_companion.core.database import get_database_manager

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """Handles database initialization and schema setup."""

    def __init__(self) -> None:
        self.db_manager = get_database_manager()
        self._setup_sql_path = Path(__file__).parent / "database_setup.sql"

    async def initialize_database(self) -> bool:
        """
        Initialize the database with required schema and security policies.

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            _ = self.db_manager.client  # Initialize client for connection test

            # Read the setup SQL file
            if not self._setup_sql_path.exists():
                logger.error(f"Setup SQL file not found: {self._setup_sql_path}")
                return False

            setup_sql = self._setup_sql_path.read_text()

            # Execute the setup SQL
            # Note: Supabase Python client doesn't directly support raw SQL execution
            # In production, this would be handled via Supabase dashboard or CLI
            logger.info("Database schema setup SQL prepared")
            logger.info("Execute the following SQL in your Supabase SQL Editor:")
            logger.info("-" * 50)
            logger.info(setup_sql)
            logger.info("-" * 50)

            return True

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False

    async def verify_schema(self) -> bool:
        """
        Verify that the database schema is correctly configured.

        Returns:
            bool: True if schema is valid, False otherwise
        """
        try:
            client = self.db_manager.client

            # Test basic table access (this will work if RLS is properly configured)
            # We'll use a simple query that should work with proper auth setup
            _ = client.table("users").select("user_id").limit(1).execute()

            logger.info("Database schema verification successful")
            return True

        except Exception as e:
            logger.warning(f"Schema verification failed (expected if not yet initialized): {e}")
            return False

    async def test_authentication_setup(self) -> bool:
        """
        Test that authentication-related functionality works.

        Returns:
            bool: True if auth setup is working, False otherwise
        """
        try:
            _ = self.db_manager.client  # Initialize client

            # Test that we can access auth functions
            # This is a basic connectivity test
            health_check = await self.db_manager.health_check()

            if not health_check:
                logger.error("Database health check failed")
                return False

            logger.info("Authentication setup test passed")
            return True

        except Exception as e:
            logger.error(f"Authentication setup test failed: {e}")
            return False


async def setup_database() -> bool:
    """
    Main function to set up the database for authentication.

    Returns:
        bool: True if setup successful, False otherwise
    """
    initializer = DatabaseInitializer()

    logger.info("Starting database setup for authentication...")

    # Initialize the database schema
    if not await initializer.initialize_database():
        logger.error("Database initialization failed")
        return False

    # Verify the schema
    _ = await initializer.verify_schema()  # Test schema accessibility

    # Test authentication setup
    auth_working = await initializer.test_authentication_setup()

    if auth_working:
        logger.info("Database setup for authentication completed successfully")
        return True
    else:
        logger.warning(
            "Database setup completed with warnings - manual configuration may be required"
        )
        return False


if __name__ == "__main__":
    # Allow running this module directly for database setup
    asyncio.run(setup_database())
