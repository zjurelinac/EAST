"""
    setup.py
    =============
    Setup configuration for east module

"""


from setuptools import setup, find_packages


setup(
    name='east',
    version='1.0.1',
    description='Flask extension for creating REST APIs',
    author='Zvonimir Jurelinac',
    author_email='zjurelinac@gmail.com',
    url='https://github.com/zjurelinac/East',
    license='MIT',
    keywords='flask rest',
    packages=find_packages(),
    install_requires=['peewee>=2.8.3', 'Flask>=0.11.1', 'mistune>=0.7.3',
                      'Pygments>=2.1.3', 'PyJWT>=1.4.2'],
    package_data={
        'east': ['assets/styles/default.css', 'assets/docs_template.html'],
    },
)
