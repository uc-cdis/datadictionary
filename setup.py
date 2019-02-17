from setuptools import setup, find_packages

setup(
    name='gdcdictionary',
    version='1.1.0',
    packages=find_packages(),
    install_requires=[
        'PyYAML>=3.11',
        'jsonschema>=2.5.1',
    ],
    package_data={
        "gdcdictionary": [
            "schemas/*.yaml",
            "schemas/projects/*.yaml",
            "schemas/projects/*/*.yaml",
        ]
    },
)
