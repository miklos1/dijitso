#!/usr/bin/env python

import sys, platform, re
from os.path import join, split, pardir
from distutils.core import setup

if sys.version_info < (2, 7):
    print("Python 2.7 or higher required, please upgrade.")
    sys.exit(1)

scripts = [join("scripts", "dijitso")]

#man1 = [join("doc", "man", "man1", "dijitso.1.gz")]

if platform.system() == "Windows" or "bdist_wininst" in sys.argv:
    # In the Windows command prompt we can't execute Python scripts
    # without a .py extension. A solution is to create batch files
    # that runs the different scripts.
    for script in scripts:
        batch_file = script + ".bat"
        with open(batch_file, "w") as f:
            f.write('python "%%~dp0\%s" %%*\n' % split(script)[1])
        scripts.append(batch_file)

version = re.findall('__version__ = "(.*)"',
                     open('dijitso/__init__.py', 'r').read())[0]

setup(name = "dijitso",
      version = version,
      description = "Distributed just-in-time building of shared libraries",
      author = "Martin Sandve Alnæs",
      author_email = "martinal@simula.no",
      url = "http://www.fenicsproject.org",
      packages = ['dijitso'],
      package_dir = {'dijitso': 'dijitso'},
      scripts = scripts,
      #data_files = [(join("share", "man", "man1"), man1)]
      )
