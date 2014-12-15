# -*- coding: utf-8 -*-
"""
Initialize the logger

Created on December 15, 2014

Copyright Alpes Lasers SA, Neuchatel, Switzerland, 2014

@author: chiesa
"""
import logging

pkg = "alchemyjson"
try:
    from logserviceclient.utils.logger import initLogger
    try:
        initLogger(pkg)
    except Exception:
        logging.warning("Log service client was not initialized properly")
except ImportError:
    pass