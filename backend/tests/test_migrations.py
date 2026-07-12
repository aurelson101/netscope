from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

def test_migrations_upgrade_and_downgrade(tmp_path,monkeypatch):
    database=tmp_path/"migration.db";monkeypatch.setenv("DATABASE_URL",f"sqlite+aiosqlite:///{database}")
    config=Config(str(Path(__file__).parents[1]/"alembic.ini"));config.set_main_option("script_location",str(Path(__file__).parents[1]/"alembic"));config.set_main_option("sqlalchemy.url",f"sqlite:///{database}")
    command.upgrade(config,"head")
    tables=set(inspect(create_engine(f"sqlite:///{database}")).get_table_names())
    assert {"users","user_sessions","scan_schedules","vrfs","dhcp_reservations","configuration_versions"} <= tables
    assert {"vrf_id","parent_id"} <= {column["name"] for column in inspect(create_engine(f"sqlite:///{database}")).get_columns("ipam_prefixes")}
    command.downgrade(config,"base")
    assert "users" not in inspect(create_engine(f"sqlite:///{database}")).get_table_names()
