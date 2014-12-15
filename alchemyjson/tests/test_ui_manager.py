from alchemyjson.manager import Manager
from alchemyjson.tests.initializer import populate_test_db
from alchemyjson.tests.mapping import Employees
from alchemyjson.tests.mapping import Managers as MyManagers

__author__ = 'chiesa'

if __name__ == "__main__":
    db = populate_test_db()
    m = Manager(dbConnection=db)
    m.add_model(Employees)
    m.add_model(MyManagers)
    print m.select('managers', {'functions':[{'name':'count',
                                       'field':'id'}]})
    print m.select('employees', {'functions':[{'name':'count',
                                       'field':'id'}]})

