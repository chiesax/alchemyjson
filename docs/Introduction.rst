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
a simple and homogeneous interface to query (and in the future possibly also update, insert
and delete) database tables and their relations.

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
    almanager = Manager(dbConnection=db)
    almanager.add_model(Employees)
    almanager.add_model(MyManagers)
    print almanager.select('managers', {'functions':[{'name':'count',
                   'field':'id'}]})
    print almanager.select('employees', {'functions':[{'name':'count',
                   'field':'id'}]})

These calls will actually apply the SQL function count to both models and return
the number of rows in the table.



By default, a model is referenced by its table name. It is also possible
to specify the name of the model within the :py:class:`alchemyjson.Manager`::

    almanager.add_model(MyManagers, name='managers2')
    almanager.select('managers2')

It is of course possible to query rows. To query all the rows in the table::

    print almanager.select('managers')

.. note::
    Results are paginated, with a default maximum number of
    rows per page set to 100.

Or we may select all managers whose name equals 'johnny', order them by
descending order and limit the result to 2 rows::

    print almanager.select('managers', {'filters':[{'name':'name',
                                            'op':'eq',
                                            'val':'johnny'}],
                                'order_by':[{'field':'name',
                                       'direction':'desc'}],
                                'limit':2,
                                'offset':0})


By default only the table rows are returned, not relationships. But this is also
easy::

    almanager.select('managers', {'to_dict': {'deep':{'employees':[]}},
                          'joinedload': ['employees']})

This tells :py:mod:`alchemyjson` to return the employees relationship as a list.

.. note::
    The joinedload option makes the query more efficient as only one select statement is actually
    executed, note however that this is not the default behavior.

--------------------------
JSON conversion
--------------------------

Results returned by select, and arguments to select are actually
plain python dictionaries. It is however quite straightforward
to convert them to JSON::

    almanager.to_json(almanager.select('employees'))

The reason we do not do this by default is that conversion of some python
types to JSON is not supported in python, as for instance :py:mod:`datetime`
objects, :py:class:`decimal.Decimal` or :py:class:`numpy.array`, and the
conversion may be use case specific. This can be customized by initializing the
:py:class:`alchemyjson.Manager` with your json encoder. In this example
we show the default encoder used by :py:mod:`alchemyjson`::

    import json
    class MyJsonEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, datetime.datetime):
                return obj.isoformat()
            elif isinstance(obj, datetime.date):
                return obj.isoformat()
            elif isinstance(obj, datetime.timedelta):
                return (datetime.datetime.min + obj).time().isoformat()
            elif isinstance(obj, decimal.Decimal):
                return float(obj)
            elif type(obj).__name__ == 'ndarray':
                return list(obj)
            else:
                return super(MyJsonEncoder, self).default(obj)

    m2 = Manager(dbConnection=db, encoder=MyJsonEncoder())


