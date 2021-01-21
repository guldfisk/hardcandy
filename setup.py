import os

from setuptools import setup


def package_files(directory):
    paths = []
    for path, directories, file_names in os.walk(directory):
        for filename in file_names:
            paths.append(os.path.join('..', path, filename))
    return paths


extra_files = package_files('hardcandy')

setup(
    name = 'hardcandy',
    version = '1.0',
    packages = ['hardcandy'],
    package_data = {'': extra_files},
    include_package_data = True,
    install_requires = [
        'yeetlong @ https://github.com/guldfisk/yeetlong/tarball/master#egg=yeetlong-1.0',
    ],
)
