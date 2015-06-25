==========================
Select
==========================

As explained in the introduction, the method to be used for selecting
table rows is :meth:`select <alchemyjson.manager.Manager.select>`.

The `queryDict` parameter of this method specifies both the search parameters and the
returned data. It is of the form::

   {
   "filters": [{"name": "age", "op": "lt", "val": 20}, ...],
   "order_by": [{"field": "age", "direction": "desc"}, ...],
   "limit": 10,
   "offset": 3,
   "disjunction": True,
   "joinedload" : ["employees"],
   "to_dict": {"deep":{"employees":[]}},
   "functions" : [{"name":"count", "field":"id"}, {"name":"sum", "field":"id"}, ...]
   }

filters
----------

It is a list of filter specifications, where every item of the list has the form::

   {"name": "<field name of the SQLAlchemy column attribute>",
    "op": "<the name of the operator for the filter>",
    "val": "<a value to apply the operator>",
    "otherfield": "<the name of another column attribute to apply the operator>"}

This is the list of currently supported operators for filter specifications:

.. csv-table:: filter_specifications
   :header:    op, description, val or otherfield

   is_null, field = NULL , not used
   is_not_null, field != NULL, not used
   ==, field = (val or otherfield), either one or the other
   eq, field = (val or otherfield), either one or the other
   equals, field = (val or otherfield), either one or the other
   equals_to, field = (val or otherfield), either one or the other
   !=, field != (val or otherfield), either one or the other
   ne, field != (val or otherfield), either one or the other
   neq, field != (val or otherfield), either one or the other
   not_equal_to, field != (val or otherfield), either one or the other
   does_not_equal, field != (val or otherfield), either one or the other
   >, field > (val or otherfield), either one or the other
   gt, field > (val or otherfield), either one or the other
   <, field < (val or otherfield), either one or the other
   lt, field < (val or otherfield), either one or the other
   >=, field >= (val or otherfield), either one or the other
   ge, field >= (val or otherfield), either one or the other
   gte, field >= (val or otherfield), either one or the other
   geq, field >= (val or otherfield), either one or the other
   <=, field <= (val or otherfield), either one or the other
   le, field <= (val or otherfield), either one or the other
   lte, field <= (val or otherfield), either one or the other
   leq, field <= (val or otherfield), either one or the other
   ilike, field ILIKE val, val is a match string; otherfield not used
   like,  field LIKE val, val is a match string; otherfield not used
   in, field IN val, val is a list of values; otherfield not used
   not_in, field NOT IN val, val is a list of values; otherfield not used


order_by
---------------

It is a list of order by specifications, where every item of the list has the
form::

   {"field": "<field name of the SQLAlchemy attribute>",
    "direction": "<the name of the operator for the direction>",
    "nullsmode": "<optional, specify how NULL values are handled>"}

where directions is either *asc* or *desc*. The ``nullsmode`` optional specification
if either *nullslast* or *nullsfirts*, note that this is not supported by all
database backends.


.. autoclass:: alchemyjson.manager.Manager
   :members: select