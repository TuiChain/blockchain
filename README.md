<!-- ----------------------------------------------------------------------- -->

# TuiChain: Blockchain

[![Build status](https://github.com/TuiChain/blockchain/workflows/build/badge.svg?branch=main)](https://github.com/TuiChain/blockchain/actions)

Repository for the blockchain component of the TuiChain application.

## Structure

The whole repo is a Python package named *tuichain-ethereum*.
Python code is under `tuichain/`.
Python tests are under `test/`.

Directory `truffle/` is a Truffle setup.
Contracts are under `truffle/contracts/`.
Mock contracts for tests are under `truffle/contracts/mocks/`.
Actual JavaScript and Solidity tests are under `truffle/test/`.

The Python setup uses the Truffle setup to compile the contracts and include the necessary results in the Python package installation.
Thus to install this package you must have `npm` installed beforehand.

## Using the Python layer

Simply install using pip with local or remote path to repo, *e.g.*:

- `pip install my-repos/blockchain`, or
- `pip install https://github.com/TuiChain/blockchain/archive/main.zip`

Note: You can also give the Git URL to `pip install`, but using the zip archive as above usually installs faster.

## Development setup

To develop contracts move to directory `truffle/` and use:

- `npm install` to install the Truffle setup dependencies;
- `npm run compile` to compile the contracts;
- `npm test` to run all linters and tests.

To develop the Python layer, create a virtualenv and install the Python package in "editable" mode, *e.g.*:

- `cd my-repos/blockchain`
- `virtualenv env`
- `cd env`
- `source bin/activate`
- `pip install -e ..[test]`

You can then run the tests from the repo root with `tox`, which runs mypy and black and then uses pytest to run the actual tests. You can also just run `pytest test` to skip the mypy and black steps and speed up things. Note that you will have to rerun the `pip install -e ..[test]` in the virtualenv whenever the Solidity contracts are modified.

Configuration files for PyCharm are also provided:

- Open the repo in PyCharm and configure an interpreter named "tuichain-ethereum" that uses the virtualenv.
- The PyCharm project has a "tox" run configuration to run the tests.
- The PyCharm project also has a "pytest" run configuration to run just the pytest part of the tests directly in the project's interpreter, which is faster;
- Optionally install plugin "mypy" (by Roberto Leinardi) to integrate mypy with PyCharm.
- Optionally install plugin "File Watchers" to have black run after every file save.

<!-- ----------------------------------------------------------------------- -->
