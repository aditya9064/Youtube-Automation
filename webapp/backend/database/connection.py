"""
Database Connection Configuration
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from typing import Generator, AsyncGenerator
import asyncio

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./youtube_automation.db")
ASYNC_DATABASE_URL = os.getenv("ASYNC_DATABASE_URL", "sqlite+aiosqlite:///./youtube_automation.db")

# Create synchronous engine (for compatibility with existing code)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False  # Set to True for SQL debugging
)

# Create asynchronous engine for FastAPI
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False  # Set to True for SQL debugging
)

# Session makers
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Dependency for getting database session (sync)
def get_database() -> Generator[Session, None, None]:
    """Get synchronous database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency for getting async database session
async def get_async_database() -> AsyncGenerator[AsyncSession, None]:
    """Get asynchronous database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Database utilities
class DatabaseManager:
    """Database management utilities"""
    
    @staticmethod
    def create_tables():
        """Create all database tables (sync)"""
        from .models import Base
        Base.metadata.create_all(bind=engine)
    
    @staticmethod
    async def create_tables_async():
        """Create all database tables (async)"""
        from .models import Base
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    @staticmethod
    def drop_tables():
        """Drop all database tables (sync)"""
        from .models import Base
        Base.metadata.drop_all(bind=engine)
    
    @staticmethod
    async def drop_tables_async():
        """Drop all database tables (async)"""
        from .models import Base
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    
    @staticmethod
    def reset_database():
        """Reset database by dropping and recreating tables"""
        DatabaseManager.drop_tables()
        DatabaseManager.create_tables()
    
    @staticmethod
    async def reset_database_async():
        """Reset database by dropping and recreating tables (async)"""
        await DatabaseManager.drop_tables_async()
        await DatabaseManager.create_tables_async()

# Connection testing
def test_connection() -> bool:
    """Test database connection"""
    try:
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            return result.fetchone()[0] == 1
    except Exception as e:
        print(f"Database connection test failed: {e}")
        return False

async def test_async_connection() -> bool:
    """Test async database connection"""
    try:
        async with async_engine.connect() as conn:
            result = await conn.execute("SELECT 1")
            row = result.fetchone()
            return row[0] == 1
    except Exception as e:
        print(f"Async database connection test failed: {e}")
        return False

# Initialize database on import
def init_database():
    """Initialize database with default configuration"""
    try:
        # Test connection
        if test_connection():
            print(f"Database connected successfully: {DATABASE_URL}")
            
            # Create tables
            DatabaseManager.create_tables()
            print("Database tables created/verified")
            
            return True
        else:
            print("Database connection failed")
            return False
            
    except Exception as e:
        print(f"Database initialization error: {e}")
        return False

# Export main components
__all__ = [
    "engine",
    "async_engine", 
    "SessionLocal",
    "AsyncSessionLocal",
    "get_database",
    "get_async_database",
    "DatabaseManager",
    "test_connection",
    "test_async_connection",
    "init_database"
]

if __name__ == "__main__":
    # Test database connection when run directly
    print("Testing database connection...")
    if init_database():
        print("✅ Database setup successful!")
    else:
        print("❌ Database setup failed!")