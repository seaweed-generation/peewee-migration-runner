from pathlib import Path
from playhouse.migrate import SchemaMigrator
from peewee import Model, CharField

DEFAULT_DIR = Path.cwd() / 'migrations'


class SchemaMigration(Model):
    filename = CharField(primary_key=True)

    class Meta:
        table_name = 'schemamigration'


class MigrationRunner:
    def __init__(self, db, migrations_dir: Path = DEFAULT_DIR):
        if not migrations_dir.exists():
            raise ValueError(
                f'Migrations directory "{migrations_dir}" does not exist.')

        self.db = db
        self.pw_migrator = SchemaMigrator.from_database(db)
        self.migrations_dir = migrations_dir

        SchemaMigration.bind(db)
        db.create_tables([SchemaMigration])
        self.model = SchemaMigration

    def run(self):
        for migration_file in self._unapplied_files():
            self._apply_migration(migration_file)

    def rollback(self):
        last_migration = self.model.select().order_by(
            self.model.filename.desc()
        ).get_or_none()

        if last_migration:
            file: Path = self.migrations_dir / last_migration.filename

            if not file.exists():
                raise FileNotFoundError(
                    f"Previously run migration file {last_migration} does not exist (looking in {self.migrations_dir})"
                )

            self._apply_rollback(file, last_migration)

    def _unapplied_files(self):
        files = self.migrations_dir.glob('*.py')
        applied = set(m.filename for m in self.model.select())
        todo = []

        for file in files:
            if not file.name in applied:
                todo.append(file)

        todo.sort(key=lambda p: p.name)

        return todo

    def _apply_migration(self, migration_file: Path):
        migrate, _ = self._read_file(migration_file)

        with self.db.atomic():
            migrate(self.pw_migrator)
            self.model.create(filename=migration_file.name)

    def _apply_rollback(self, migration_file: Path, migration_record: SchemaMigration):
        _, rollback = self._read_file(migration_file)

        if not rollback:
            raise NameError(
                f'Cannot rollback with {migration_file.name}, rollback function not defined')

        with self.db.atomic():
            rollback(self.pw_migrator)
            migration_record.delete_instance()

    def _read_file(self, file: Path):
        code = file.read_text()
        ast = compile(code, '<string>', 'exec', dont_inherit=True)
        file_globals = {}
        exec(ast, file_globals, None)

        if not file_globals['migrate']:
            raise NameError(
                'Migration file does not contain a migrate function.')

        return file_globals['migrate'], file_globals['rollback']
