# -*- coding: utf-8 -*-
from __future__ import print_function

from setuptools import setup
from os.path import join, split
import re
import sys
import platform
import codecs

module_name = "dijitso"

if sys.version_info < (2, 7):
    print("Python 2.7 or higher required, please upgrade.")
    sys.exit(1)

# __init__.py has UTF-8 characters. Works in Python 2 and 3.
version = re.findall('__version__ = "(.*)"',
                     codecs.open(join(module_name, '__init__.py'), 'r',
                                 encoding='utf-8').read())[0]

url = "https://bitbucket.org/fenics-project/%s/" % module_name
tarball = None
if 'dev' not in version:
    tarball = url + "downloads/%s-%s.tar.gz" % (module_name, version)

script_names = ("dijitso-version", "dijitso-cache")

scripts = [join("scripts", script) for script in script_names]
man_files = [join("doc", "man", "man1", "%s.1.gz" % (script,)) for script in script_names]
data_files = [(join("share", "man", "man1"), man_files)]

if platform.system() == "Windows" or "bdist_wininst" in sys.argv:
    # In the Windows command prompt we can't execute Python scripts
    # without a .py extension. A solution is to create batch files
    # that runs the different scripts.
    for script in scripts:
        batch_file = script + ".bat"
        with open(batch_file, "w") as f:
            f.write(sys.excecutable + ' "%%~dp0\%s" %%*\n' % split(script)[1])
        scripts.append(batch_file)

CLASSIFIERS = """\
Development Status :: 5 - Production/Stable
Intended Audience :: Developers
Intended Audience :: Science/Research
License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)
Operating System :: POSIX
Operating System :: POSIX :: Linux
Operating System :: MacOS :: MacOS X
Operating System :: Microsoft :: Windows
Programming Language :: Python
Programming Language :: Python :: 2
Programming Language :: Python :: 2.7
Programming Language :: Python :: 3
Programming Language :: Python :: 3.4
Programming Language :: Python :: 3.5
Programming Language :: Python :: 3.6
Topic :: Scientific/Engineering :: Mathematics
Topic :: Software Development :: Libraries :: Python Modules
"""

requires = ["numpy", "six"]
if sys.version_info[0] == 2:
    requires.append("subprocess32")

setup(name="dijitso",
      version=version,
      description="Distributed just-in-time building of shared libraries",
      author="Martin Sandve Alnæs",
      author_email="martinal@simula.no",
      url=url,
      download_url=tarball,
      classifiers=[_f for _f in CLASSIFIERS.split('\n') if _f],
      scripts=scripts,
      packages=["dijitso"],
      package_dir={'dijitso': 'dijitso'},
      install_requires=requires,
      data_files=data_files
      )
