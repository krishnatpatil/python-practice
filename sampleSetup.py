from setuptools import setup, find_packages

setup(
    name='sample-project-name',
    version='1.0.0.1',
    python_requires='>=3.6',
    description='Project description',
    author='kripatil',
    author_email="test@example.com",
    packages=find_packages('SOURCES/scripts'),
    package_dir={'': 'SOURCES/scripts'},
    include_package_data=True,
    install_requires=['requests', 'click', 'pathlib', 'configparser',],
    entry_points={'console_scripts': ['test=test_client:cli']},
)

