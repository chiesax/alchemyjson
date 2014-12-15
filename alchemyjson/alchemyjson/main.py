# -*- coding: utf-8 -*-
"""
tool to jsonify interaction with sqlalchemy

Created on December 15, 2014

Copyright Alpes Lasers SA, Neuchatel, Switzerland, 2014

@author: chiesa
"""
from alchemyjson.utils.parser import parser
import logging
try:
    from configuration_manager import gConfig
except ImportError:
    from configuration_manager_light import gConfig


class Main(object):
    """
    Base class
    """
    def __init__(self):
        """
        C'tor
        """
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.addHander(logging.StreamHandler())

    def run(self):
        """
        This method is called at run time. 
        """
        self.log.info("Logging something")
        return
        
def main():
    #parser.add_argument("-X", "--X", help="Some option", dest="somevar")
    options = parser.parse_args()
    # Do something with the options, like pass them to the class below
    app = Main()
    app.run()
    