from alchemyjson.manager import Manager

__author__ = 'chiesa'

from alchemyjson.tests.initializer import populate_test_db
from alchemyjson.tests.mapping import Employees, Managers

# -*- coding: utf-8 -*-
"""
Created on December 15, 2014

Copyright Alpes Lasers SA, Neuchatel, Switzerland, 2014

@author: chiesa
"""

import unittest

class TestMain(unittest.TestCase):

    DB = None
    manager = None

    @classmethod
    def setUpClass(cls):
        cls.DB = populate_test_db()
        cls.manager = Manager(cls.DB)
        cls.manager.add_model(Employees)
        cls.manager.add_model(Managers)

    def test_select(self):
        rsp1 = self.manager.select('managers', {'functions':[{'name':'count',
                                           'field':'id'}]})
        self.assertDictEqual(rsp1, {'count__id':1})
        rsp2 = self.manager.select('employees', {'functions':[{'name':'count',
                                                            'field':'id'}]})
        self.assertDictEqual(rsp2, {'count__id':4})
        rsp3 = self.manager.select('managers', {'filters':[{'name':'name',
                                                               'op':'eq',
                                                               'val':'johnny'}],
                                                'order_by':[{'field':'name',
                                                                'direction':'desc'}],
                                                'limit':2,
                                                'offset':0})
        self.assertDictEqual(rsp3, {'num_results':1,
                                    'objects':[{'id':1, 'name':'johnny'}],
                                    'page':1,
                                    'total_pages':1})
        rsp4 = self.manager.select('managers', {'order_by':[{'field':'name',
                                         'direction':'desc'}],
                                         'limit':2,
                                         'offset':0})
        self.assertEqual(rsp4['num_results'], 1)
        rsp5 = self.manager.select('employees', {'filters':[{'name':'name',
                                                             'op':'eq',
                                                             'field':'surname'}]})
        self.assertEqual(rsp5['num_results'], 1)

    def test_has_any(self):
        rsp = self.manager.select('managers',
                                  {'filters': [{'name': 'employees',
                                                'op': 'any',
                                                'val': {'name': 'name',
                                                        'op': 'eq',
                                                        'val': 'jack'}}]})
        self.assertEqual(rsp['num_results'], 1)
        rsp = self.manager.select('managers',
                                  {'filters': [{'name': 'employees',
                                                'op': 'any',
                                                'val': {'name': 'name',
                                                        'op': 'eq',
                                                        'val': 'qqq'}}]})
        self.assertEqual(rsp['num_results'], 0)
        rsp = self.manager.select('managers',
                                  {'filters': [{'name': 'employees__name',
                                                'op': 'any',
                                                'field': 'name'}]})
        self.assertEqual(rsp['num_results'], 0)

    def test_deep_select(self):

        rsp5 = self.manager.select('managers',
                                   {'to_dict': {'deep':{'employees':[]}},
                                   'joinedload': ['employees']})
        pass

    def test_composite_junction(self):
        rsp = self.manager.select('employees', {'filters': [{'junk': 'and',
                                                            'filters': [{'junk': 'or',
                                                                         'filters': [{'name': 'name',
                                                                                      'op': 'eq',
                                                                                      'val': 'jack'},
                                                                                     {'name': 'name',
                                                                                      'op': 'eq',
                                                                                      'val': 'francy'}]},
                                                                         {'junk': 'or',
                                                                          'filters': [{'name': 'surname',
                                                                                       'op': 'eq',
                                                                                       'val': 'j'}]}]}]})
        self.assertEqual(rsp['num_results'], 1)
