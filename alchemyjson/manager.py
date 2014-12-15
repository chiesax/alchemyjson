from contextlib import closing
import decimal
import math
import json
import datetime
from sqlalchemy.exc import OperationalError
from sqlalchemy.inspection import inspect
from sqlalchemy.sql.functions import func
from alchemyjson.utils.helpers import to_dict, evaluate_functions, count, primary_key_names
from alchemyjson.utils.search import SearchParameters, create_query, OPERATORS

__author__ = 'chiesa'

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

class Manager(object):

    def __init__(self, dbConnection, maxResultsPerPage=100):
        self.dbConnection = dbConnection
        self.models = {}
        self._encoder = MyJsonEncoder()
        self._maxResultsPerPage = maxResultsPerPage


    def add_model(self, model, name=None):
        if not name:
            name = inspect(model).mapped_table.name
        if name in self.models:
            raise ValueError, 'model with name {0} already added'.format(name)
        self.models[name] = model

    def get_model(self, modelName):
        return self.models[modelName]

    def select_by_unique(self, modelName, value, fieldName="id"):
        model = self.get_model(modelName)
        with closing(self.dbConnection.get_session()) as session:
            inst = session.query(model).filter(getattr(model, fieldName) == value).\
                            one()
            return to_dict(inst)

    def to_json(self, myDict):
        return self._encoder.encode(myDict)



    #TODO: maxPerPage actually queries the database for the whole query set
    def select(self, modelName, queryDict=None, page=1, maxPerPage=None):
        if not queryDict: queryDict = {}
        model = self.get_model(modelName)
        with closing(self.dbConnection.get_session()) as session:
            sp = SearchParameters.from_dictionary(queryDict)
            q = create_query(session, model, sp)
            is_single = queryDict.get('single')
            functions = queryDict.get('functions')
            if is_single:
                return to_dict(q.one())
            elif functions:
                return self._evaluate_functions(session, model, functions,
                                                sp)
            else:
                obj = q.all()
                if maxPerPage is None:
                    maxPerPage = self._maxResultsPerPage
                return self._paginated(obj, page_num=page,
                                       results_per_page=maxPerPage)


    def _paginated(self, instances, page_num, results_per_page):
        """Returns a paginated JSONified response from the specified list of
        model instances.
        `instances` is either a Python list of model instances or a
        :class:`~sqlalchemy.orm.Query`.
        The response data is JSON of the form:
        .. sourcecode:: javascript
           {
             "page": 2,
             "total_pages": 3,
             "num_results": 8,
             "objects": [{"id": 1, "name": "Jeffrey", "age": 24}, ...]
           }
        """
        num_results = len(instances)
        if results_per_page > 0:
            # get the page number (first page is page 1)
            start = (page_num - 1) * results_per_page
            end = min(num_results, start + results_per_page)
            total_pages = int(math.ceil(float(num_results) / results_per_page))
        else:
            page_num = 1
            start = 0
            end = num_results
            total_pages = 1
        objects = [to_dict(x) for x in instances[start:end]]
        return dict(page=page_num, objects=objects, total_pages=total_pages,
                    num_results=num_results)

    def _create_query(self, session, model, search_params):
        """Builds an SQLAlchemy query instance based on the search parameters
        present in ``search_params``, an instance of :class:`SearchParameters`.
        This method returns a SQLAlchemy query in which all matched instances
        meet the requirements specified in ``search_params``.
        `model` is SQLAlchemy declarative model on which to create a query.
        `search_params` is an instance of :class:`SearchParameters` which
        specify the filters, order, limit, offset, etc. of the query.
        Building the query proceeds in this order:
        1. filtering the query
        2. ordering the query
        3. limiting the query
        4. offsetting the query
        Raises one of :exc:`AttributeError`, :exc:`KeyError`, or
        :exc:`TypeError` if there is a problem creating the query. See the
        documentation for :func:`_create_operation` for more information.
        """
        # Adding field filters
        query = session.query
        # may raise exception here
        filters = self._create_filters(model, search_params)
        query = query.filter(search_params.junction(*filters))

        # Order the search. If no order field is specified in the search
        # parameters, order by primary key.
        if search_params.order_by:
            for val in search_params.order_by:
                field = getattr(model, val.field)
                direction = getattr(field, val.direction)
                query = query.order_by(direction())
        else:
            pks = primary_key_names(model)
            pk_order = (getattr(model, field).asc() for field in pks)
            query = query.order_by(*pk_order)

        # Limit it
        if search_params.limit:
            query = query.limit(search_params.limit)
        if search_params.offset:
            query = query.offset(search_params.offset)
        return query

    def _create_filters(self, model, search_params):
        """Returns the list of operations on `model` specified in the
        :attr:`filters` attribute on the `search_params` object.
        `search-params` is an instance of the :class:`SearchParameters` class
        whose fields represent the parameters of the search.
        Raises one of :exc:`AttributeError`, :exc:`KeyError`, or
        :exc:`TypeError` if there is a problem creating the query. See the
        documentation for :func:`_create_operation` for more information.
        Pre-condition: the ``search_params.filters`` is a (possibly empty)
        iterable.
        """
        filters = []
        for filt in search_params.filters:
            fname = filt.fieldname
            val = filt.argument
            # get the relationship from the field name, if it exists
            relation = None
            if '__' in fname:
                relation, fname = fname.split('__')
            # get the other field to which to compare, if it exists
            if filt.otherfield:
                val = getattr(model, filt.otherfield)
            # for the sake of brevity...
            create_op = self._create_operation
            param = create_op(model, fname, filt.operator, val, relation)
            filters.append(param)
        return filters

    def _create_operation(self, model, fieldname, operator, argument, relation=None):
        """Translates an operation described as a string to a valid SQLAlchemy
        query parameter using a field or relation of the specified model.
        More specifically, this translates the string representation of an
        operation, for example ``'gt'``, to an expression corresponding to a
        SQLAlchemy expression, ``field > argument``. The recognized operators
        are given by the keys of :data:`OPERATORS`. For more information on
        recognized search operators, see :ref:`search`.
        If `relation` is not ``None``, the returned search parameter will
        correspond to a search on the field named `fieldname` on the entity
        related to `model` whose name, as a string, is `relation`.
        `model` is an instance of a SQLAlchemy declarative model being
        searched.
        `fieldname` is the name of the field of `model` to which the operation
        will be applied as part of the search. If `relation` is specified, the
        operation will be applied to the field with name `fieldname` on the
        entity related to `model` whose name, as a string, is `relation`.
        `operation` is a string representating the operation which will be
         executed between the field and the argument received. For example,
         ``'gt'``, ``'lt'``, ``'like'``, ``'in'`` etc.
        `argument` is the argument to which to apply the `operator`.
        `relation` is the name of the relationship attribute of `model` to
        which the operation will be applied as part of the search, or ``None``
        if this function should not use a related entity in the search.
        This function raises the following errors:
        * :exc:`KeyError` if the `operator` is unknown (that is, not in
          :data:`OPERATORS`)
        * :exc:`TypeError` if an incorrect number of arguments are provided for
          the operation (for example, if `operation` is `'=='` but no
          `argument` is provided)
        * :exc:`AttributeError` if no column with name `fieldname` or
          `relation` exists on `model`
        """
        # raises KeyError if operator not in OPERATORS
        opfunc = OPERATORS[operator]
        argspec = inspect.getargspec(opfunc)
        # in Python 2.6 or later, this should be `argspec.args`
        numargs = len(argspec[0])
        # raises AttributeError if `fieldname` or `relation` does not exist
        field = getattr(model, relation or fieldname)
        # each of these will raise a TypeError if the wrong number of argments
        # is supplied to `opfunc`.
        if numargs == 1:
            return opfunc(field)
        if argument is None:
            msg = ('To compare a value to NULL, use the is_null/is_not_null '
                   'operators.')
            raise TypeError(msg)
        if numargs == 2:
            return opfunc(field, argument)
        return opfunc(field, argument, fieldname)

    def _evaluate_functions(self, session, model, functions, search_params):
        """Executes each of the SQLAlchemy functions specified in ``functions``, a
        list of dictionaries of the form described below, on the given model and
        returns a dictionary mapping function name (slightly modified, see below)
        to result of evaluation of that function.
        `session` is the SQLAlchemy session in which all database transactions will
        be performed.
        `model` is the SQLAlchemy model class on which the specified functions will
        be evaluated.
        ``functions`` is a list of dictionaries of the form::
            {'name': 'avg', 'field': 'amount'}
        For example, if you want the sum and the average of the field named
        "amount"::
            >>> # assume instances of Person exist in the database...
            >>> f1 = dict(name='sum', field='amount')
            >>> f2 = dict(name='avg', field='amount')
            >>> evaluate_functions(Person, [f1, f2])
            {'avg__amount': 456, 'sum__amount': 123}
        The return value is a dictionary mapping ``'<funcname>__<fieldname>'`` to
        the result of evaluating that function on that field. If `model` is
        ``None`` or `functions` is empty, this function returns the empty
        dictionary.
        If a field does not exist on a given model, :exc:`AttributeError` is
        raised. If a function does not exist,
        :exc:`sqlalchemy.exc.OperationalError` is raised. The former exception will
        have a ``field`` attribute which is the name of the field which does not
        exist. The latter exception will have a ``function`` attribute which is the
        name of the function with does not exist.
        """
        if not model or not functions:
            return {}
        processed = []
        funcnames = []
        for function in functions:
            funcname, fieldname = function['name'], function['field']
            # We retrieve the function by name from the SQLAlchemy ``func``
            # module and the field by name from the model class.
            #
            # If the specified field doesn't exist, this raises AttributeError.
            funcobj = getattr(func, funcname)
            try:
                field = getattr(model, fieldname)
            except AttributeError as exception:
                exception.field = fieldname
                raise exception
            # Time to store things to be executed. The processed list stores
            # functions that will be executed in the database and funcnames
            # contains names of the entries that will be returned to the
            # caller.
            funcnames.append('{0}__{1}'.format(funcname, fieldname))
            processed.append(funcobj(field))
        # Evaluate all the functions at once and get an iterable of results.
        try:
            filters = self._create_filters(model, search_params)
            query = session.query(*processed)
            evaluated = query.filter(search_params.junction(*filters)).one()
        except OperationalError as exception:
            # HACK original error message is of the form:
            #
            #    '(OperationalError) no such function: bogusfuncname'
            original_error_msg = exception.args[0]
            bad_function = original_error_msg[37:]
            exception.function = bad_function
            raise exception
        return dict(zip(funcnames, evaluated))


