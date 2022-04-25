"""Installation script"""
import setuptools

with open("README.md", "r") as file:
    description = file.read()

with open('requirements.txt') as f:
    required = f.read().splitlines()

setuptools.setup(
    name="Debian package statistics tool",
    version="1.0",
    author="Gulsum Atici",
    author_email="gulsumatici@canonical.com",
    description="A tool for OSM Gridfs unused file operations",
    long_description=description,
    long_description_content_type="text/markdown",
    install_requires=required,
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    entry_points={
    'console_scripts': [
        'gridfsclean=gridfsclean.gridfsclean:run_cli',
        ],
    },
)