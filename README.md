<!-- ----------------------------------------------------------------------- -->

# TuiChain: Blockchain

[![Build status](https://github.com/TuiChain/blockchain/workflows/build/badge.svg?branch=main)](https://github.com/TuiChain/blockchain/actions)

Repository for the blockchain component of the TuiChain application.

<!-- ----------------------------------------------------------------------- -->

## For users

### Brief intro to the TuiChain blockchain architecture

An instance of the entire on-chain TuiChain infrastructure is composed of:

- a *controller* contract,
- a *market* contract, and
- any number of *loan* contracts.

The idea for the final application is to have a single instance of this contract infrastructure deployed in the Ethereum mainnet.
In practice we will use local chains for testing and development and also the public Ropsten testnet.

Initially, only the controller and market contracts exist.
Every time a loan is created, a loan contract is deployed.
The market contracts and all loan contracts are reachable from the controller contract, which ties the whole thing together.

Visit the [wiki](https://github.com/TuiChain/blockchain/wiki), for more information about the [design models](https://github.com/TuiChain/blockchain/wiki/Design-Models) which sustain the implementation.

### How to use this repo

This whole repo is a Python package named `tuichain_ethereum`.
First install `npm` and then install the Python package using pip with a local or remote path to the repo, *e.g.*:

- `pip install my-repos/blockchain`, or
- `pip install https://github.com/TuiChain/blockchain/archive/main.zip`

Then just `import tuichain_ethereum`.
All exported symbols are documented in the code.
Synopsis of provided types:

- Basic Ethereum-related types:

  - `Address` - the address of an Ethereum account or contract
  - `PrivateKey` - the private key of an Ethereum account
  - `Transaction[T]` - a handle to an Ethereum transaction

- Simple TuiChain-specific types:

  - `SellPosition` - represents a market sell position
  - `LoanIdentifier` - uniquely identifies a loan
  - `LoanPhase(Enum)` - enumeration of the possible phases of a loan
  - `LoanState` - holds the mutable part of a loan's state

- Types providing access to the on-chain infrastructure:

  - `Controller` - represents an instance of the *controller* contract
  - `Market` - represents an instance of the *market* contract
  - `Loans` - represents a collection of instances of the *loan* contract
  - `Loan` - represents an instance of the *loan* contract

- Helper types for building transactions to be signed and submitted by users:

  - `MarketUserTransactionBuilder` - to build transactions interacting with *market* contracts
  - `LoanUserTransactionBuilder` - to build transactions interacting with *loan* contracts

Deploy an instance of TuiChain's Ethereum infrastructure with `Controller.deploy()` or connect to an existing controller contract with `Controller()` and go from there.

<!-- ----------------------------------------------------------------------- -->

## For developers

### Repo structure

Python code is under `tuichain_ethereum/`.
Python tests are under `test/`.

Directory `truffle/` is a Truffle setup.
Contracts are under `truffle/contracts/`.
Mock contracts for tests are under `truffle/contracts/mocks/`.
Actual JavaScript and Solidity tests are under `truffle/test/`.

The Python setup uses the Truffle setup to compile the contracts and include the relevant output in the Python package installation.
Thus to install this package you must have `npm` installed.

### Development setup

To work on the contracts, go to `truffle/` and use:

- `npm install` to install the Truffle setup dependencies;
- `npm run truffle compile` to compile the contracts;
- `npm run prettier` to reformat all code;
- `npm test` to run all linters and tests.

To develop the Python layer, create a virtualenv and install the Python package in "editable" mode with the `[test]` extras, *e.g.*:

- `cd my-repos/blockchain`
- `virtualenv .env`
- `source .env/bin/activate`
- `pip install --use-feature=2020-resolver -e .[test]`

You can then run the tests from the repo root with `tox`, which runs mypy and black in a clean environment and then uses pytest to run the actual tests.
You can also just run `pytest test` to skip the mypy and black steps and speed up things, but this can lead to unreproducible test results.
Note that you will have to reinstall the Python package in the virtualenv whenever the Solidity contracts are modified:

- `pip uninstall -y tuichain_ethereum`
- `pip install --use-feature=2020-resolver -e .[test]`

Configuration files for PyCharm are also provided:

- Open the repo in PyCharm and configure an interpreter named "tuichain_ethereum" that uses the virtualenv.
- The PyCharm project has a "tox" run configuration to run the tests.
- The PyCharm project also has a "pytest" run configuration to run just the pytest part of the tests directly in the project's interpreter;
- Optionally install plugin "mypy" (by Roberto Leinardi) to integrate mypy with PyCharm.
- Optionally install plugin "File Watchers" to have black run after every file save.

### GitHub Actions

The GitHub Actions setup runs all aforementioned tests on every push and pull request.

<!-- ----------------------------------------------------------------------- -->
