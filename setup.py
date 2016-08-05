from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

long_description = """
Pushkin is a free open source tool for sending push notifications. It was
developed with a focus on speed and enabling fast experimentation.  Pushkin was
mainly built for supporting online mobile games, but can easily be extended to
any type of application. It supports both Android and iOS platforms.
"""

setup(
    name='pushkin',
    version='0.1.4b',

    description='Pushkin is a free open source tool for sending push notifications',
    long_description=long_description,

    url='https://github.com/Nordeus/pushkin.git',

    author='Nordeus LLC',
    author_email='pushkin.dev@nordeus.com',
    license='MIT',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Utilities',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7'
    ],

    # What does your project relate to?
    keywords='development push notifications mobile',

    packages=find_packages(exclude=['docs']),

    setup_requires=['pytest-runner'],
    install_requires=[
        # Only used for tests
        'pytest>=2.8.5',
        'pytest-mock>=0.9.0',
        'funcsigs>=0.4.0',
        'mock>=1.3.0',
        'pytest-tornado>=0.4.4',

        'tornado>=4.2.1',
        'configparser>=3.3.0',
        'protobuf>=2.6.1',
        'psycopg2>=2.6',
        'requests>=2.9.1',
        'sqlalchemy>=1.0.12',
        'alembic>=0.8.6'
        ],
    package_data = {
        '': ['*.sql', '*.sh', '*.ini', '*.mako']
    },

    entry_points={
        'console_scripts': [
            'pushkin=pushkin.pushkin_cli:main',
        ],
    },
)
