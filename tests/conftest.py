"""
Shared test fixtures and configuration
"""
import asyncio
from typing import AsyncGenerator
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
import unittest.mock

from backend.models import Base
from backend.models.law_firm import Firm
from backend.models.law_user import User, UserRole
from backend.core.security import create_access_token


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="session")
async def test_session_factory(test_engine):
    """Create test session factory"""
    return async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest.fixture
async def test_db(test_session_factory) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    async with test_session_factory() as session:
        yield session


@pytest.fixture
async def firm_a(test_db: AsyncSession):
    """Create test firm A"""
    firm = Firm(
        name="Test Firm A",
        email="firm_a@test.com",
        city="Amritsar",
        state="Punjab",
        plan="solo"
    )
    test_db.add(firm)
    await test_db.commit()
    await test_db.refresh(firm)
    return firm


@pytest.fixture
async def firm_b(test_db: AsyncSession):
    """Create test firm B"""
    firm = Firm(
        name="Test Firm B",
        email="firm_b@test.com",
        city="Ludhiana",
        state="Punjab",
        plan="solo"
    )
    test_db.add(firm)
    await test_db.commit()
    await test_db.refresh(firm)
    return firm


@pytest.fixture
async def firm_a_user(firm_a, test_db: AsyncSession):
    """Create test user for firm A"""
    user = User(
        firm_id=firm_a.id,
        name="Test Lawyer A",
        email="lawyer_a@test.com",
        hashed_password="hashed_password",
        role=UserRole.LAWYER
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def firm_b_user(firm_b, test_db: AsyncSession):
    """Create test user for firm B"""
    user = User(
        firm_id=firm_b.id,
        name="Test Lawyer B",
        email="lawyer_b@test.com",
        hashed_password="hashed_password",
        role=UserRole.LAWYER
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
def firm_a_token(firm_a_user, firm_a):
    """Create JWT token for firm A user"""
    return create_access_token({
        "sub": str(firm_a_user.id),
        "firm_id": str(firm_a.id),
        "vertical": "law"
    })


@pytest.fixture
def firm_b_token(firm_b_user, firm_b):
    """Create JWT token for firm B user"""
    return create_access_token({
        "sub": str(firm_b_user.id),
        "firm_id": str(firm_b.id),
        "vertical": "law"
    })


@pytest.fixture
def firm_a_id(firm_a):
    """Get firm A ID"""
    return str(firm_a.id)


@pytest.fixture
def firm_b_id(firm_b):
    """Get firm B ID"""
    return str(firm_b.id)


# Mock Azure services
@pytest.fixture(autouse=True)
def mock_azure_services():
    """Mock all Azure services to avoid real API calls during testing"""
    # Mock Azure OpenAI
    with unittest.mock.patch('backend.services.llm_service.AsyncAzureOpenAI') as mock_openai:
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create.return_value = type('MockResponse', (), {
            'choices': [type('MockChoice', (), {
                'message': type('MockMessage', (), {'content': '{"response": "mocked"}'})()
            })()]
        })()

        # # Mock Azure Search - commented out as SearchClient may not be directly imported
        # with unittest.mock.patch('backend.services.search_service.SearchClient') as mock_search:
        #     mock_search_client = mock_search.return_value
        #     mock_search_client.search.return_value = []

        # # Mock Azure Blob Storage - commented out as BlobServiceClient may not be directly imported
        # with unittest.mock.patch('backend.services.document_service.BlobServiceClient') as mock_blob:
        #     mock_blob_client = mock_blob.return_value
        #     mock_container_client = type('MockContainer', (), {})()
        #     mock_blob_client.get_container_client.return_value = mock_container_client
        #     mock_container_client.upload_blob.return_value = None
        #     mock_container_client.download_blob.return_value = type('MockDownloader', (), {
        #         'readall': lambda: b'mocked file content'
        #     })()

        yield