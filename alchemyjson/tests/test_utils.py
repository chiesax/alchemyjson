from contextlib import closing
from alchemyjson.tests.initializer import populate_test_db
from alchemyjson.tests.mapping import Employees
from alchemyjson.utils.search import SearchParameters, create_query

__author__ = 'chiesa'

# -*- coding: utf-8 -*-
"""
Created on December 15, 2014

Copyright Alpes Lasers SA, Neuchatel, Switzerland, 2014

@author: chiesa
"""

import unittest

class TestMain(unittest.TestCase):

    DB = None

    @classmethod
    def setUpClass(cls):
        cls.DB = populate_test_db()

    def test_search(self):
        with closing(self.DB.get_session()) as session:
            sp = SearchParameters.from_dictionary({'filters':[{'name':'name',
                                                               'op':'eq',
                                                               'val':'michael'}],
                                                   'order_by':[{'field':'name',
                                                                'direction':'desc'}],
                                                   'limit':2,
                                                   'offset':0})
            q = create_query(session, Employees, sp)
            e = q.one()
            self.assertEqual(e.name,'michael')


