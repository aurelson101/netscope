from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

def test_migrations_upgrade_and_downgrade(tmp_path,monkeypatch):
    database=tmp_path/"migration.db";monkeypatch.setenv("DATABASE_URL",f"sqlite+aiosqlite:///{database}")
    config=Config(str(Path(__file__).parents[1]/"alembic.ini"));config.set_main_option("script_location",str(Path(__file__).parents[1]/"alembic"));config.set_main_option("sqlalchemy.url",f"sqlite:///{database}")
    command.upgrade(config,"head")
    tables=set(inspect(create_engine(f"sqlite:///{database}")).get_table_names())
    assert {"users","user_sessions","scan_schedules","vrfs","dhcp_reservations","configuration_versions","passive_connectors","passive_event_receipts"} <= tables
    inspector=inspect(create_engine(f"sqlite:///{database}"))
    assert {"vrf_id","parent_id"} <= {column["name"] for column in inspector.get_columns("ipam_prefixes")}
    for table in ("asset_addresses","ipam_addresses","scan_jobs","scan_schedules"):
        assert "vrf_id" in {column["name"] for column in inspector.get_columns(table)}
    assert {"progress","current_module","result_count"} <= {column["name"] for column in inspector.get_columns("scan_jobs")}
    command.downgrade(config,"base")
    assert "users" not in inspect(create_engine(f"sqlite:///{database}")).get_table_names()

def test_upgrade_adds_hierarchy_columns_to_legacy_database(tmp_path,monkeypatch):
    database=tmp_path/"legacy.db";sync_url=f"sqlite:///{database}";async_url=f"sqlite+aiosqlite:///{database}"
    engine=create_engine(sync_url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE ipam_prefixes (id VARCHAR(36) PRIMARY KEY, prefix VARCHAR(64))"))
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"))
        connection.execute(text("INSERT INTO alembic_version(version_num) VALUES ('0001_initial_schema')"))
    monkeypatch.setenv("DATABASE_URL",async_url)
    config=Config(str(Path(__file__).parents[1]/"alembic.ini"));config.set_main_option("script_location",str(Path(__file__).parents[1]/"alembic"))
    command.upgrade(config,"head")
    assert {"vrf_id","parent_id"} <= {column["name"] for column in inspect(engine).get_columns("ipam_prefixes")}
