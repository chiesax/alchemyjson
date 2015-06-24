from contextlib import closing
import decimal
import math
import json
import datetime
from sqlalchemy.exc import OperationalError
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.functions import func
from alchemyjson.utils.helpers import to_dict, evaluate_functions, count, primary_key_names, has_field, get_columns, \
    get_relations, strings_to_dates
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

    NULL_RESULT = dict(num_results=0,
                       objects=[],
                       total_pages=0,
                       page=1)

    def __init__(self, dbConnection, maxResultsPerPage=100,
                 encoder=None):
        self.dbConnection = dbConnection
        self.models = {}
        self.modelDictKargs = {}
        self._encoder = encoder
        if self._encoder is None:
            self._encoder = MyJsonEncoder()
        self._maxResultsPerPage = maxResultsPerPage

    def add_model(self, model, name=None, toDictKargs=None):
        if not name:
            name = inspect(model).mapped_table.name
        if name in self.models:
            raise ValueError('model with name {0} already added'.format(name))
        self.models[name] = model
        self.modelDictKargs[name] = toDictKargs or {}

    def get_model(self, modelName):
        return self.models[modelName]

    def select_by_unique(self, modelName, value, fieldName="id"):
        model = self.get_model(modelName)
        with closing(self.dbConnection.get_session()) as session:
            inst = session.query(model).filter(getattr(model, fieldName) == value).\
                            one()
            return to_dict(inst, **self.modelDictKargs[modelName])

    def to_json(self, myDict):
        return self._encoder.encode(myDict)

    def select(self, modelName, queryDict=None, page=1, maxPerPage=None):
        """
        Issue a SELECT statement on the table corresponding to modelName.
        Results are paginaged and the page to be returned or the maximum
        number of results per table may be specified.
        :param modelName: the name of the model within
        :param queryDict: if not specified, then the whole table
        will be queried. It is a dictionary of the form::
            {
              'filters': [{'name': 'age', 'op': 'lt', 'val': 20}, ...],
              'order_by': [{'field': 'age', 'direction': 'desc'}, ...]
              'limit': 10,
              'offset': 3,
              'disjunction': True,
              'to_dict': {'deep':{'employees':[]}},

            }
        where:
            * ``filters`` is the list of filter specifications,
            * ``order_by`` is the list of order by specifications,
            * ``limit`` is the maximum number of total matching entries to return,
            * ``offset`` is the number of initial entries to skip in
                    the matching result set,
            * ``disjunction`` is whether the filters should be joined as a disjunction (AND) or conjunction (OR),
                    defaults to True
            * ``to_dict`` specifies the configuration for the SQLAlchemy objects serializer.
            * ``joinedload`` specifies a list of relations to be loaded using the
               SQLAlchemy joinedload strategy (by default lazy load is used which
               is not very efficient when serializing relations)
        :param page: the page number to be returned
        :param maxPerPage: the maximum number of results per page, defaults
        to the maxResultsPerPage attribute,
        :return dict: a dictionary of the form:
        .. sourcecode:: javascript
           {
             "page": 2,
             "total_pages": 3,
             "num_results": 8,
             "objects": [{"id": 1, "name": "Jeffrey", "age": 24}, ...]
           }
        This may depends on some queryDict parameters,
        to decide for instance whether related models should be returned
        as well. Here num_results is the total number of results matching the queryDict.
        As said, however, only maxPerPage results will be returned by each select.
        """
        if not queryDict: queryDict = {}
        model = self.get_model(modelName)
        modelDictKargs = self.modelDictKargs[modelName]
        with closing(self.dbConnection.get_session()) as session:
            sp = SearchParameters.from_dictionary(queryDict)
            q = create_query(session, model, sp)
            is_single = queryDict.get('single')
            functions = queryDict.get('functions')
            todict = queryDict.get('to_dict', {})
            modelDictKargs.update(todict)
            jload = queryDict.pop('joinedload', None)
            if jload:
                q = q.options(*(joinedload(x) for x in jload))
            if is_single:
                return to_dict(q.one(), **modelDictKargs)
            elif functions:
                return self._evaluate_functions(session, model, functions,
                                                sp)
            else:
                if maxPerPage is None:
                    maxPerPage = self._maxResultsPerPage
                return self._paginated(q, page_num=page,
                                       results_per_page=maxPerPage,
                                       model_dict_kargs=modelDictKargs)

    def _paginated(self, query, page_num, results_per_page, model_dict_kargs=None,
                   relload=None):
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
        num_results = query.count()
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
        objects = [to_dict(x, **(model_dict_kargs or {})) for x in query[start:end]]
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


