from contextlib import closing
from tempfile import NamedTemporaryFile
from sqlalchemy.engine import create_engine
from sqlalchemy.orm.session import sessionmaker
from alchemyjson.tests.mapping import Managers, BASE, Employees


class DBConnection(object):
    def __init__(self, engine, filename):
        self.filename = filename
        self._engine = engine
        self._sessionFactory = sessionmaker(bind=self._engine)

    def get_session(self):
        return self._sessionFactory()

    def close(self):
        self._engine.dispose()


def create_temp_db(filePath):
    engine = create_engine('sqlite:///{0}'.format(filePath))
    BASE.metadata.create_all(engine)
    return DBConnection(engine=engine, filename = filePath)

def populate_test_db():
    tmpFile = NamedTemporaryFile(prefix='alchemyjson_test',delete=False)
    tmpFile.close()
    dbConnection = create_temp_db(tmpFile.name)
    m1 = Managers(name='johnny')
    e1 = Employees(name='michael', surname='michael')
    e2 = Employees(name='jack', surname='j')
    e3 = Employees(name='jilly', surname='j')
    e4 = Employees(name='francy', surname='f')
    m1.employees = [e1, e2, e3, e4]
    with closing(dbConnection.get_session()) as session:
        session.add(m1)
        session.commit()
    return dbConnection

if __name__ == "__main__":
    c = populate_test_db()
    print c.filename







