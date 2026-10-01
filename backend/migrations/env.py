from alembic import context

from app.core.config import Settings
from app.db.base import Base
from app.db.session import build_engine

# Importar os modelos aqui quando forem implementados, para registrar seu metadata.
target_metadata = Base.metadata
settings = Settings()

if context.is_offline_mode():
    context.configure(
        url=settings.database_url.get_secret_value(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = build_engine(settings)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()
