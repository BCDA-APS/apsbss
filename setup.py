#!/usr/bin/env python

"""
Packaging setup for apsbss.
"""

import pathlib
import setuptools
import versioneer

import apsbss as package


__entry_points__ = {
    "console_scripts": [
        "apsbss = apsbss:main",
    ],
    # 'gui_scripts': [],
}
long_description = (pathlib.Path(__file__).parent / "README.md").read_text()


setuptools.setup(
    author=package.__author__,
    author_email=package.__author_email__,
    classifiers=package.__classifiers__,
    description=package.__description__,
    entry_points=__entry_points__,
    license=package.__license__,
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=package.__install_requires__,
    name=package.__project__,
    # platforms        = package.__platforms__,
    packages=setuptools.find_packages(exclude=package.__exclude_project_dirs__),
    include_package_data=True,
    url=package.__url__,
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    zip_safe=package.__zip_safe__,
    python_requires=package.__python_version_required__,
)
