#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on December 15, 2014

Copyright Alpes Lasers SA, Neuchatel, Switzerland, 2014

@author: chiesa
"""

from setuptools import setup

setup(
    setup_requires=['pbr'],
    pbr=True,
    test_suite = "alchemyjson.tests"
)