# blockchain
Blockchain Repository for the TuiChain Application

## Startup

If truffle not installed yet:
```bash
npm install -g truffle
```

## Compile

To compile the contracts within contracts folder, you have to be in the project root:
```bash
truffle compile
```

## Deploy contracts
T
o run migrations in a development environment:
```bash
truffle develop
```

To run all migrations located within your project's migrations directory:
```bash
truffle migrate
```
If your migrations were previously run successfully, truffle migrate will start execution from the last migration that was run, running only newly created migrations.

To run all your migrations from the beginning:
```bash
truffle migrate --reset
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

