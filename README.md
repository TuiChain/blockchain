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

Note: You can also give the Git URL to `pip install`, but using the zip archive as above usually installs much faster.

## Development setup

To develop contracts, first install truffle globally using `npm install -g truffle`.
Then, when in directory `truffle/`, use:

- `npm install` to install the Truffle setup's dependencies;
- `truffle compile` to compile the contracts;
- `truffle test` to run all tests;
- `truffle test <path>` to run a specific test.

To run the Python tests, install tox with `pip install tox` and run the `tox` command in the repo root.
To be able to import the package from an interpreter for ad hoc testing, create a virtualenv and install the Python package in "editable" mode, *e.g.*:

- `cd my-repos/blockchain`
- `virtualenv env`
- `cd env`
- `source bin/activate`
- `pip install -e ..`

<!-- ----------------------------------------------------------------------- -->
