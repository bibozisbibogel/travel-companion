"""Tests for database initialization and authentication setup."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from travel_companion.core.database_init import DatabaseInitializer, setup_database


class TestDatabaseInitializer:
    """Test cases for DatabaseInitializer."""

    @pytest.fixture
    def initializer(self):
        """Create a DatabaseInitializer instance for testing."""
        with patch("travel_companion.core.database_init.get_database_manager") as mock_db_manager:
            mock_manager = Mock()
            mock_db_manager.return_value = mock_manager
            yield DatabaseInitializer()

    @pytest.mark.asyncio
    async def test_initialize_database_success(self, initializer):
        """Test successful database initialization."""
        with patch.object(initializer, "_setup_sql_path") as mock_path:
            mock_path.exists.return_value = True
            mock_path.read_text.return_value = "CREATE TABLE test;"

            result = await initializer.initialize_database()
            assert result is True

    @pytest.mark.asyncio
    async def test_initialize_database_missing_sql_file(self, initializer):
        """Test database initialization with missing SQL file."""
        with patch.object(initializer, "_setup_sql_path") as mock_path:
            mock_path.exists.return_value = False

            result = await initializer.initialize_database()
            assert result is False

    @pytest.mark.asyncio
    async def test_initialize_database_exception(self, initializer):
        """Test database initialization with exception."""
        with patch.object(initializer, "_setup_sql_path") as mock_path:
            mock_path.exists.side_effect = Exception("File error")

            result = await initializer.initialize_database()
            assert result is False

    @pytest.mark.asyncio
    async def test_verify_schema_success(self, initializer):
        """Test successful schema verification."""
        mock_client = Mock()
        mock_table = Mock()
        mock_select = Mock()
        mock_limit = Mock()

        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.limit.return_value = mock_limit
        mock_limit.execute.return_value = Mock()

        initializer.db_manager.client = mock_client

        result = await initializer.verify_schema()
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_schema_failure(self, initializer):
        """Test schema verification failure."""
        mock_client = Mock()
        mock_client.table.side_effect = Exception("Table not found")
        initializer.db_manager.client = mock_client

        result = await initializer.verify_schema()
        assert result is False

    @pytest.mark.asyncio
    async def test_test_authentication_setup_success(self, initializer):
        """Test successful authentication setup test."""
        initializer.db_manager.health_check = AsyncMock(return_value=True)

        result = await initializer.test_authentication_setup()
        assert result is True

    @pytest.mark.asyncio
    async def test_test_authentication_setup_failure(self, initializer):
        """Test authentication setup test failure."""
        initializer.db_manager.health_check = AsyncMock(return_value=False)

        result = await initializer.test_authentication_setup()
        assert result is False

    @pytest.mark.asyncio
    async def test_test_authentication_setup_exception(self, initializer):
        """Test authentication setup test with exception."""
        initializer.db_manager.health_check = AsyncMock(side_effect=Exception("Connection failed"))

        result = await initializer.test_authentication_setup()
        assert result is False


class TestSetupDatabase:
    """Test cases for setup_database function."""

    @pytest.mark.asyncio
    async def test_setup_database_success(self):
        """Test successful database setup."""
        with patch(
            "travel_companion.core.database_init.DatabaseInitializer"
        ) as mock_initializer_class:
            mock_initializer = Mock()
            mock_initializer.initialize_database = AsyncMock(return_value=True)
            mock_initializer.verify_schema = AsyncMock(return_value=True)
            mock_initializer.test_authentication_setup = AsyncMock(return_value=True)
            mock_initializer_class.return_value = mock_initializer

            result = await setup_database()
            assert result is True

    @pytest.mark.asyncio
    async def test_setup_database_initialization_failure(self):
        """Test database setup with initialization failure."""
        with patch(
            "travel_companion.core.database_init.DatabaseInitializer"
        ) as mock_initializer_class:
            mock_initializer = Mock()
            mock_initializer.initialize_database = AsyncMock(return_value=False)
            mock_initializer_class.return_value = mock_initializer

            result = await setup_database()
            assert result is False

    @pytest.mark.asyncio
    async def test_setup_database_auth_failure_with_warning(self):
        """Test database setup with auth test failure but still returns False."""
        with patch(
            "travel_companion.core.database_init.DatabaseInitializer"
        ) as mock_initializer_class:
            mock_initializer = Mock()
            mock_initializer.initialize_database = AsyncMock(return_value=True)
            mock_initializer.verify_schema = AsyncMock(return_value=True)
            mock_initializer.test_authentication_setup = AsyncMock(return_value=False)
            mock_initializer_class.return_value = mock_initializer

            result = await setup_database()
            assert result is False
