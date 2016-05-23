import os

from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-throttled-logger',
    version='1.0',
    packages=find_packages(),
    include_package_data=True,
    url='http://github.com/mennanov/django-throttled-logger',
    license='The MIT License (MIT)',
    author='Renat Mennanov',
    author_email='renat@mennanov.com',
    description='Django throttled email logger',
    long_description=README,
)
