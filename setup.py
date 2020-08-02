# this file was taken as template from https://github.com/coursera-dl/coursera-dl/blob/master/setup.py

from setuptools import setup
from asteg import __version__

def read_file(filename, alt=None):
    """
    Read the contents of filename or give an alternative result instead.
    """
    lines = None

    try:
        with open(filename, encoding='utf-8') as f:
            lines = f.read()
    except IOError:
        lines = [] if alt is None else alt
    return lines


requirements = read_file('requirements.txt')

setup(
    name='asteg',
    version=__version__,
    maintainer='Ibrahim Rafi',
    maintainer_email='me@ibrahimrafi.me',

    license='MIT',
    url='https://github.com/rafiibrahim8/asteg',

    install_requires=requirements,

    description='Steganography : Hiding text or file inside an audio',
    keywords=['asteg', 'steganography', 'audio'],

    packages=["asteg"],
    entry_points=dict(
        console_scripts=[
            'asteg=asteg.asteg_cli:main'
        ]
    ),

    platforms=['any'],
)
