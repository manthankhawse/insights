from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlmodel import SQLModel, text
from db.models.data_source import DataSource

DATABASE_URL = "postgresql+asyncpg://admin:admin@localhost:5432/da_agent_db"

engine = create_async_engine(
    url=DATABASE_URL,
    echo=False
)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        statement = text("SELECT 'hello';")
        result = await conn.execute(statement)
        print(f"DB Connection Test: {result.scalar()}")


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)