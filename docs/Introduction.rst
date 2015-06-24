============================
Introduction
============================

The scope of the package is to provide a JSON based interface to interact
with a database mapped by SQLAlchemy.

This is very useful when constructing a N-tier based infrastructure, where
clients do not interact directly with the database, but though a server. This
has many advantages:

    * the clients do not know about the database structure, so the database
      structure can change without affecting the clients;
    * business logic can be implemented in the server;
    * the server can be optimized for efficient database interaction;
    * implement an abstract authentication layer;

:py:mod:`alchemyjson` then helps constructing such an infrastructure by providing
a simple interface to query (and in the future possibly also update, insert
and delete) database tables.

This package has been adapted from the :py:mod:`flask-restless` package.

-----------------------------
Examples
-----------------------------

Lets start with a very simple database mapping, which can be found in :py:mod:`alchemyjson.tests`::

    class Managers(BASE):

        __tablename__ = 'managers'

        id = Column(Integer, primary_key=True)
        name = Column(String)

    class Employees(BASE):

        __tablename__ = 'employees'

        id = Column(Integer, primary_key=True)
        name = Column(String)
        manager_id = Column(Integer, ForeignKey('managers.id'))

        manager = relationship(Managers, backref='employees')

Then let's create an interface using :py:mod:`alchemyjson`::

    from alchemyjson.tests.initializer import populate_test_db
    from alchemyjson.manager import Manager
    from alchemyjson.tests.mapping import Employees
    from alchemyjson.tests.mapping import Managers as MyManagers

    db = populate_test_db()
    m = Manager(dbConnection=db)
    m.add_model(Employees)
    m.add_model(MyManagers)
    print m.select('managers', {'functions':[{'name':'count',
                   'field':'id'}]})
    print m.select('employees', {'functions':[{'name':'count',
                   'field':'id'}]})

These calls will actually apply the SQL function count to both models and return
the number of rows in the table.

By default, a model is referenced by its table name. It is also possible
to specify the name of the model within the :py:class:`alchemyjson.Manager`::

    m.add_model(MyManagers, name='managers2')
    m.select('managers2')

It is of course possible to query rows. To query all the rows in the table::

    print m.select('managers')

.. note::
    Results are paginated, with a default maximum number of
    rows per page set to 100.

Or we may select all managers whose name equals 'johnny', order them by
descending order and limit the result to 2 rows::

    print m.select('managers', {'filters':[{'name':'name',
                                            'op':'eq',
                                            'val':'johnny'}],
                                'order_by':[{'field':'name',
                                       'direction':'desc'}],
                                'limit':2,
                                'offset':0})


By default only the table rows are returned, not relationships. But this is also
easy::

    m.select('managers', {'to_dict': {'deep':{'employees':[]}},
                          'joinedload': ['employees']})

This tells :py:mod:`alchemyjson` to return the employees relationship as a list.

.. note::
    The joinedload option makes the query more efficient as only one select statement is actually
    executed, note however that this is not the default behavior.


