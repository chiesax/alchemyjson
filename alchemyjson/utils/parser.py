# -*- coding: utf-8 -*-
"""
Created on December 15, 2014

Copyright Alpes Lasers SA, Neuchatel, Switzerland, 2014

@author: chiesa
"""

import argparse
try:
    from configuration_manager import cfg_parser
except ImportError:
    from configuration_manager_light import cfg_parser


parser = argparse.ArgumentParser(parents=[cfg_parser])