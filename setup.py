from setuptools import setup, find_packages

setup(
    name='ceti',
    description='CLI data ingestion tools for Project CETI',
    author='Nikolay Pavlov, Peter Malkin',
    author_email='me@nikolaypavlov.com, petermalkin@google.com',
    version="1.0.0",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(),
    install_requires=[
        'findssh~=1.5.0',
        'paramiko~=2.7.2',
    ],
    entry_points={
        'console_scripts': [
            'ceti = ceti.cli:main'
        ],
    }
)
