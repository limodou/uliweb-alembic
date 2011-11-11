from alembic import context
from sqlalchemy import engine_from_config
from logging.config import fileConfig
config = context.config

fileConfig(config.config_file_name)

engine = engine_from_config(
            config.get_section('alembic'), prefix='sqlalchemy.')

if not context.requires_connection():
    context.configure(dialect_name=engine.name)
    context.run_migrations()
else:
    connection = engine.connect()
    context.configure(connection=connection, dialect_name=engine.name)

    trans = connection.begin()
    try:
        context.run_migrations()
        trans.commit()
    except:
        trans.rollback()
        raise