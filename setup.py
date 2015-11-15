from setuptools import setup, find_packages

setup(
    name='Ene IRC',
    version='0.1.0',
    description='Ene IRC',
    long_description='Ene IRC',
    author='Makoto Fujimoto',
    author_email='makoto@makoto.io',
    url='https://github.com/FujiMakoto/Ene-IRC',
    license='MIT',
    classifiers=[
        'Development Status :: 1 - Planning',
        'License :: OSI Approved :: MIT License',
    ],
    packages=find_packages(),
    entry_points={
        'ene_irc.plugins': [
            'datetime = ene_irc.plugins.datetime:DateTime',
            'logging = ene_irc.plugins.logging:Logger',
            'test = ene_irc.plugins.test:Test'
        ]
    },
    install_requires=['twisted>=15.4.0,<15.5', 'sqlalchemy>=1.0.9,<1.1', 'alembic>=0.8.3,<0.9', 'pymysql>=0.6.7,<0.7',
                      'voluptuous>=0.8.7,<0.9', 'appdirs>=1.4.0,<1.5', 'agentml>=0.3.1,<0.4', 'venusian>=1.0,<1.1',
                      'ircmessage>=0.1,<0.2'],
    test_requires=['mock>=1.3,<1.4', 'coveralls>=1.1,<1.2'],
    package_data={
        'ene_irc': ['config/*.cfg'],
    },
)
