from setuptools import setup, find_packages


with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name='ceti',
    description='CLI data ingestion tools for Project CETI',
    author='Nikolay Pavlov, Peter Malkin',
    author_email='me@nikolaypavlov.com, petermalkin@google.com',
    version="1.0.20",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.7",
    packages=find_packages(),
    install_requires=[
        'findssh~=1.5.0',
        'paramiko>=2.10.1',
        'boto3~=1.17.78',
        'tqdm~=4.60.0',
        'importlib_resources; python_version < "3.9"'
    ],
    extras_require={
        'emr': ['pyspark[sql]>=3.1.1,<3.2'],
        'test': ['pytest>=6.1.0', 'flake8>=3.8.3', 'mypy==0.812'],
    },
    entry_points={
        'console_scripts': [
            'ceti = ceti.cli:main'
        ],
    }
)
