# Peewee Migration Runner

[peewee](https://github.com/coleifer/peewee) comes with all of the parts you need to write migrations, just not a thing to run those migrations. This is a ridiculously lightweight class that's configured with a directory and a database and applies the files in in that directory in order, recording which files have been applied to a table in the database.

## Usage

Migration files are assumed to be in the current working directory + `/migrations`. The files are applied in order alphabetically. You can format the file names however you want - by date (i.e. Rails style, `20230417145000_CreateSomeTables.py`), or numerically (i.e. `001_CreateSomeTables.py`), or anything. They just have to be python files.

Each migration file _must_ define an `up` function, and _may_ define a `down` function, if you ever want to rollback. It's optional in case you don't feel like writing it until it's necessary. The functions take in an instance of the peewee `SchemaMigrator` class, and from there the rest is up to you. A template would look like:

```python
def up(migrator):
    pass

def down(migrator):
    pass
```

See the [peewee documentation](https://docs.peewee-orm.com/en/latest/peewee/playhouse.html#migrate) for what the migration implementations should look like.

Note that both functions are run inside a call to `Database.atomic()`. This may or may not have an effect, depending on your database.

Migrations are applied by creating an instance of the class with a peewee database object, then running either the `run` or `rollback` method. Typically this would be wrapped in a CLI command. For example with Flask, you'd have something like:

```python
from peewee_migration_runner import MigrationRunner

@click.command('migrate')
def run_migrations():
    MigrationRunner(get_db()).run()

@click.command('rollback')
def rollback_migrations():
    MigrationRunner(get_db()).rollback()
```

## Acknowledgements

Inspired by the runner in [peewee_migrate](https://github.com/klen/peewee_migrate), with a few key parts borrowed from that implementation.
