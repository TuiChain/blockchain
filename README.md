# Blockchain
Blockchain Repository for the TuiChain Application

## Structure

**contracts/**: Directory for Solidity contracts

**test/**: Directory for test files for testing your application and contracts

**truffle-config.js**: Truffle configuration file

## Startup

If truffle not installed yet:
```bash
npm install -g truffle
```

## Install

Install the required dependencies:
```bash
npm install
```

## Compile

To compile the contracts within contracts folder, you have to be in the project root:
```bash
truffle compile
```

## Deploy contracts
To run migrations in a development environment:
```bash
truffle develop
```

## Tests

To run all tests, simply run:
```bash
truffle test
```

Alternatively, you can specify a path to a specific file you want to run, e.g.:
```bash
truffle test ./path/to/test/file.js
```


For more info visit [Truffle docs](https://www.trufflesuite.com/docs/truffle/overview).

