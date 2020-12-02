<!-- ----------------------------------------------------------------------- -->

# TuiChain: Blockchain

[![Build status](https://github.com/TuiChain/blockchain/workflows/build/badge.svg?branch=main)](https://github.com/TuiChain/blockchain/actions)

Repository for the blockchain component of the TuiChain application.

## Structure

The whole repo is a Python package.
All Python code is under `tuichain/`.

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

To develop the Python layer, create a virtualenv and install the Python package in "editable" mode, *e.g.*:

- `cd my-repos/blockchain`
- `virtualenv env`
- `cd env`
- `source bin/activate`
- `pip install -e ..`

<!-- ----------------------------------------------------------------------- -->
