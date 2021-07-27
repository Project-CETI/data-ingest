from setuptools import setup, find_packages


with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name='ceti',
    description='CLI data ingestion tools for Project CETI',
    author='Nikolay Pavlov, Peter Malkin',
    author_email='me@nikolaypavlov.com, petermalkin@google.com',
    version="1.0.7",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.6",
    packages=find_packages(),
    install_requires=[
        'findssh~=1.5.0',
        'paramiko~=2.7.2',
        'boto3~=1.17.78',
        'tqdm~=4.60.0',
    ],
    entry_points={
        'console_scripts': [
            'ceti = ceti.cli:main'
        ],
    }
)
