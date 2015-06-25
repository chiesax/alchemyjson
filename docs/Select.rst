======
Select
======

As explained in the introduction, the method to be used for selecting
table rows is :meth:`select <alchemyjson.manager.Manager.select>`.

The ``queryDict`` parameter of this method specifies both the search parameters and the
returned data. It is of the form::

   {"filters": [{"name": "age", "op": "lt", "val": 20}, ...],
    "order_by": [{"field": "age", "direction": "desc"}, ...],
    "limit": 10,
    "offset": 3,
    "disjunction": True,
    "joinedload" : ["employees"],
    "to_dict": {"deep":{"employees":[]}},
    "functions" : [{"name":"count", "field":"id"}, {"name":"sum", "field":"id"}, ...]}

The returned structure is a dictionary of the form::

   {"page": 2,
    "total_pages": 3,
    "num_results": 8,
    "objects": [{"id": 1, "name": "Jeffrey", "age": 24}, ...]}

Here ``objects`` is a list containing the corresponding ``page`` of query
results.

.. important::
   The goal of this library is NOT to provide all functionality of SQLAlchemy,
   but rather a frequently used sub set. For more sophisticated queries,
   implementation of custom functions is recommended. The implementation of
   :meth:`select <alchemyjson.manager.Manager.select>` may then serve
   as an inspiration. Try however as far as possible to conform to the
   ``queryDict`` specification and to return a similar structure.

-------
filters
-------

It is a list of filter specifications, where every item of the list has the form::

   {"name": "<field name of the SQLAlchemy column attribute>",
    "op": "<the name of the operator for the filter>",
    "val": "<a value to apply the operator>",
    "field": "<the name of another column attribute to apply the operator>"}

This is the list of currently supported operators for filter specifications:

.. csv-table:: filter_specifications
   :header:    op, description, val or field

   is_null, field = NULL , not used
   is_not_null, field != NULL, not used
   ==, field = (val or field), either one or the other
   eq, field = (val or field), either one or the other
   equals, field = (val or field), either one or the other
   equals_to, field = (val or field), either one or the other
   !=, field != (val or field), either one or the other
   ne, field != (val or field), either one or the other
   neq, field != (val or field), either one or the other
   not_equal_to, field != (val or field), either one or the other
   does_not_equal, field != (val or field), either one or the other
   >, field > (val or field), either one or the other
   gt, field > (val or field), either one or the other
   <, field < (val or field), either one or the other
   lt, field < (val or field), either one or the other
   >=, field >= (val or field), either one or the other
   ge, field >= (val or field), either one or the other
   gte, field >= (val or field), either one or the other
   geq, field >= (val or field), either one or the other
   <=, field <= (val or field), either one or the other
   le, field <= (val or field), either one or the other
   lte, field <= (val or field), either one or the other
   leq, field <= (val or field), either one or the other
   ilike, field ILIKE val, val is a match string; field not used
   like,  field LIKE val, val is a match string; field not used
   in, field IN val, val is a list of values; field not used
   not_in, field NOT IN val, val is a list of values; field not used

------------------------
filter on related tables
------------------------

To construct a filter on a related table, the ``has`` or ``any`` operators may
be used.

   *``has``: can be used on `many to one` or `one to one` relations,
    matches rows referencing a member which meets the given criterion;
   *``any``: can be used on `one to many` or `many to many` relations,
    matches rows referencing at least one member that meets the given criterion

The filter specification item then has any of the two forms form::

   {"name": "<relation name of the model>",
    "op": "has or any",
    "val": "<filter specification item>"}

or::

   {"name": "<relation name>_<field name of the related model>",
    "op": "has or any",
    "val": "<a value to apply the operator>",
    "field": "<the name of another column attribute to apply the operator>"}

It the former case, the matching criteria on related models is quite arbitrary, however
it is not possible to specify ``field``, that is to specify a filter based on
a comparison between columns of the same model.

In the latter, an implicit filter on the related table is created matching the ``eq``
operator.

So for instance to filter all managers with at least an employee named 'jack'::

   almanager.select('managers',
                    {'filters': [{'name': 'employees',
                                  'op': 'any',
                                  'val': {'name': 'name',
                                          'op': 'eq',
                                          'val': 'jack'}}]})

Or to get all managers which have at least an employee with the same name as theirs::

   manager.select('managers',
                  {'filters': [{'name': 'employees__name',
                                'op': 'any',
                                'field': 'name'}]})

.. important::
    According to Postgresql documentation, usage of ANY or HAS operators
    is less efficient than using a JOIN.

--------
order_by
--------

It is a list of order by specifications, where every item of the list has the
form::

   {"field": "<field name of the SQLAlchemy attribute>",
    "direction": "<the name of the operator for the direction>",
    "nullsmode": "<optional, specify how NULL values are handled>"}

where directions is either *asc* or *desc*. The ``nullsmode`` optional specification
if either *nullslast* or *nullsfirts*, note that this is not supported by all
database backends.

-------
to_dict
-------

This specification controls the data returned by :meth:`select <alchemyjson.manager.Manager.select>`.

.. note::
   If the ``function`` specification is set, then the ``to_dict`` specification
   is ignored.

This has the form::

   {"deep": {"<relation name>":{"<relation name>": dict or list, ... }}, # recursive structure
    "exclude": ["<list of excluded column attributes>", ...],
    "include": ["<list of included column attributes>", ...],
    "include_relations": {"<relation name>": ["<list of included column attributes>", ...], ...},
    "exclude_relations": {"<relation name>": ["<list of excluded column attributes>", ...], ...},
    "include_methods": ["<list of computed methods of the corresponding SQLAlchemy objects>", ...]
    "include_hybrids": True or False
    }

This structure is just passed as keywords arguments to the
:func:`alchemyjson.utils.helpers.to_dict` function. For more details,
please refer to the function documentation.

.. warning::
   Only the ``deep`` and ``include_hybrids`` specifications have been tested
   at present. Also, note that the specification of ``include`` or ``exclude``
   will not affect what columns are actually queried from the database, but
   only which columns are serialized.

deep
^^^^

Is a dictionary containing a mapping from a relation name (for a
relation of `instance`) to either a list or a dictionary. This is a
recursive structure. When an empty list is encountered, the :meth:`select <alchemyjson.manager.Manager.select>`
method will return a list of table rows corresponding to the relation.

include_hybrids
^^^^^^^^^^^^^^^

Specifies whether hybrid SQLAlchemy column attributes should be returned or not.