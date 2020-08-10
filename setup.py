from setuptools import setup
from asteg import __version__

def read_file(filename):
    try:
        with open(filename, encoding='utf-8') as f:
            return f.read()
    except:
        return []

requirements = read_file('requirements.txt')
long_description = read_file('README.md')

setup(
    name='asteg',
    version=__version__,
    
    author='Ibrahim Rafi',
    author_email='me@ibrahimrafi.me',

    license='MIT',

    url='https://github.com/rafiibrahim8/asteg',
    download_url = 'https://github.com/rafiibrahim8/asteg/archive/v{}.tar.gz'.format(__version__),

    install_requires=requirements,

    description='Steganography : Hiding text or file inside an audio',
    long_description=long_description,
    long_description_content_type='text/markdown',
    keywords=['asteg', 'steganography', 'audio'],

    packages=["asteg"],
    entry_points=dict(
        console_scripts=[
            'asteg=asteg.asteg_cli:main'
        ]
    ),

    platforms=['any'],
    classifiers=[
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Science/Research',
    'Topic :: Security :: Cryptography',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
  ],
)
