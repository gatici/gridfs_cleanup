# A CLI tool for Gridfs Unused File Operations

This tools helps to find, rename, revert and delete the unused Gridfs files in OSM MongoDB.

Available operations:
- show: show unused files
- rename: rename unused files
- revert: revert back to original filename 
- delete delete all unused files

## Create Virtual Environment

```bash
python3 -m pip install --user virtualenv
python3 -m venv env
source env/bin/activate
```

## Clone the repository

```bash
git clone https://github.com/gatici/gridfs_cleanup.git && cd gridfs_cleanup
```

## Installation

This tool can be installed into your python3 environment by running:

```bash
alias env_python=`which python`
sudo $env_python setup.py install
```

## Usage

Please give the uri and operation type as arguments in the following way:
Supported operations:
- show
- rename
- revert
- delete

```bash
$env_python -m gridfsclean --uri mongodb://10.152.183.118:27017/ --operation show
$env_python -m gridfsclean --uri mongodb://10.152.183.118:27017/ --operation rename
$env_python -m gridfsclean --uri mongodb://10.152.183.118:27017/ --operation revert
$env_python-m gridfsclean --uri mongodb://10.152.183.118:27017/ --operation delete
```
