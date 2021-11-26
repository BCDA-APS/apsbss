.. _install:

Installation
============

Installation
############

The ``apsbss`` package is available for installation
by ``conda``, ``pip``, or from source.

conda
-----

If you are using Anaconda Python and have ``conda`` installed, install with this
command::

    $ conda install -c aps-anl-tag apsbss

pip
---

Released versions of *apsbss* are available on `PyPI
<https://pypi.python.org/pypi/apsbss>`_.

If you have ``pip`` installed, then you can install::

    $ pip install apsbss

source
------

The latest development versions of apsbss can be downloaded from the
GitHub repository listed above::

    $ git clone http://github.com/BCDA-APS/apsbss.git

To install in the standard Python location::

    $ cd apsbss
    $ python setup.py install

To install in user's home directory::

    $ python setup.py install --user

To install in an alternate location::

    $ python setup.py install --prefix=/path/to/installation/dir

Required Libraries
##################

The repository's ``environment.yml`` file lists the additional packages
required by ``apsbss``.  Most packages are available as conda packages
from https://anaconda.org.  The others are available on
https://PyPI.python.org.
