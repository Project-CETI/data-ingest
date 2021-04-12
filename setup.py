from setuptools import setup, find_packages 

setup(
    name='ceti',
    description='CLI data ingestion tools for Project CETI',
    author='Nikolay Pavlov',
    author_email='me@nikolaypavlov.com',
    version="1.0.0",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",        
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        'findssh',
        'paramiko',
        'wheel',
    ],
    entry_points={
        'console_scripts': [
            'ceti = ceti.cli:main'
        ],
    }
)