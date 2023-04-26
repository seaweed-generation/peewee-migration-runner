import pytest
from peewee import SqliteDatabase, Table, Model, AutoField
from peewee_migration_runner import MigrationRunner
from pathlib import Path


class MyTable(Model):
    id = AutoField()


@pytest.fixture
def db(tmp_path):
    _db = SqliteDatabase(tmp_path / 'test.db')

    with _db.connection_context():
        with MyTable.bind_ctx(_db):
            MyTable.create_table(safe=False)

            yield _db

            MyTable.drop_table(safe=False)


@pytest.fixture
def migrations_path(tmp_path):
    path: Path = tmp_path / 'migrations'
    path.mkdir(exist_ok=True)
    return path


@pytest.fixture
def runner(db, migrations_path):
    return MigrationRunner(db, migrations_path)


@pytest.fixture(autouse=True)
def migration_file(migrations_path):
    migration_text = """
from playhouse.migrate import *
import peewee as pw

def up(migrator):
    migrate(migrator.add_column('mytable', 'testcolumn', pw.IntegerField(default=0)))

def down(migrator):
    migrate(migrator.drop_column('mytable', 'testcolumn'))
"""

    path = migrations_path / '001_AddColumn.py'
    path.write_text(migration_text)


def test_up_and_down(db, runner):
    runner.run()

    columns = db.get_columns('mytable')
    assert len(columns) == 2
    assert any(c.name == 'testcolumn' for c in columns)

    migration_table = Table('schemamigration')
    migration_table.bind(db)
    filename, = migration_table.select(migration_table.c.filename).tuples().first()
    assert filename == '001_AddColumn.py'

    runner.rollback()
    columns = db.get_columns('mytable')
    assert len(columns) == 1
    assert columns[0].name == 'id'
    assert migration_table.select('1').count() == 0


def test_ignores_initial_underscore(migrations_path, db, runner):
    additional_migration = """
from playhouse.migrate import *
import peewee as pw

def up(migrator):
    migrate(migrator.add_column('mytable', 'wonthappen', pw.IntegerField(default=0)))
"""

    path = migrations_path / '_IgnoreMe.py'
    path.write_text(additional_migration)

    runner.run()

    migration_table = Table('schemamigration')
    migration_table.bind(db)
    assert migration_table.select().count() == 1

    filename, = migration_table.select(migration_table.c.filename).tuples().first()
    assert filename == '001_AddColumn.py'

    columns = db.get_columns('mytable')
    assert len(columns) == 2
    assert any(c.name == 'testcolumn' for c in columns)
    assert all(c.name != 'wonthappen' for c in columns)
