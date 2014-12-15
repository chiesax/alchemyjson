#!/bin/bash
project=$2
version=$3

pyversionshort=`python -c "from __future__ import print_function; import sys; print('{0}.{1}'.format(sys.version_info.major, sys.version_info.minor))"`

local_site_packages="${WORKON_HOME%/}/${project}/lib/python$pyversionshort/site-packages"

#here do whatever you want
#python -c "import THING; import os; print os.path.dirname(THING.__file__);"
#ln -s path/to/site-packages/mypackages $local_site_packages/
