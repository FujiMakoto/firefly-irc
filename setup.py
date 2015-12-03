import os
from setuptools import setup, find_packages


def find_data_files():
    data_files = []

    for root, dirs, files in os.walk('firefly/plugins'):
        for name in files:
            if name.endswith('.cfg') or name.endswith('.aml'):
                data_files.append(os.path.join(root, name)[8:])

    for root, dirs, files in os.walk('firefly/config'):
        for name in files:
            if name.endswith('.cfg'):
                data_files.append(os.path.join(root, name)[8:])

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
            'firefly = firefly.cli:cli',
            'firefly-config = firefly.cli.config:cli'
        ],
        'firefly_irc.plugins': [
            'auth = firefly.plugins.auth:AuthPlugin',
            'google = firefly.plugins.google:Google',
            'datetime = firefly.plugins.datetime:DateTime',
            'logging = firefly.plugins.logging:Logger',
            'seen = firefly.plugins.seen:Seen',
            'test = firefly.plugins.test:Test',
            'url = firefly.plugins.url:Url'
        ]
    },
    install_requires=['twisted>=15.4.0,<15.5', 'click>=6.2,<6.3', 'alembic>=0.8.3,<0.9', 'pymysql>=0.6.7,<0.7',
                      'voluptuous>=0.8.7,<0.9', 'appdirs>=1.4.0,<1.5', 'agentml>=0.3.1,<0.4', 'venusian>=1.0,<1.1',
                      'ircmessage>=0.1,<0.2', 'passlib>=1.6.5,<1.7', 'bcrypt>=2.0,<2.1', 'arrow>=0.7,<0.8',
                      'poogle>=0.1,<0.2'],
    package_data={
        'firefly': find_data_files(),
    },
)
