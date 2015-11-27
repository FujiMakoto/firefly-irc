import os
from setuptools import setup, find_packages


def find_data_files():
    data_files = []

    for root, dirs, files in os.walk('plugins'):
        for name in files:
            if name.endswith('.cfg') or name.endswith('.aml'):
                data_files.append(os.path.join(root, name))

    for root, dirs, files in os.walk('config'):
        for name in files:
            if name.endswith('.cfg'):
                data_files.append(os.path.join(root, name))

    return data_files


setup(
    name='Firefly IRC',
    version='0.1.0',
    description='Firefly IRC',
    long_description='Firefly IRC',
    author='Makoto Fujimoto',
    author_email='makoto@makoto.io',
    url='https://github.com/FujiMakoto/Firefly-IRC',
    license='MIT',
    classifiers=[
        'Development Status :: 1 - Planning',
        'License :: OSI Approved :: MIT License',
    ],
    packages=find_packages(exclude=['tests']),
    entry_points={
        'console_scripts': [
            'firefly = firefly.cli:cli'
        ],
        'firefly_irc.plugins': [
            'datetime = firefly.plugins.datetime:DateTime',
            'logging = firefly.plugins.logging:Logger',
            'test = firefly.plugins.test:Test'
        ]
    },
    install_requires=['twisted>=15.4.0,<15.5', 'click>=6.0,<6.1', 'alembic>=0.8.3,<0.9', 'pymysql>=0.6.7,<0.7',
                      'voluptuous>=0.8.7,<0.9', 'appdirs>=1.4.0,<1.5', 'agentml>=0.3.1,<0.4', 'venusian>=1.0,<1.1',
                      'ircmessage>=0.1,<0.2', 'arrow>=0.7,<0.8'],
    test_requires=['mock>=1.3,<1.4', 'coveralls>=1.1,<1.2'],
    package_data={
        'firefly': find_data_files(),
    },
)
