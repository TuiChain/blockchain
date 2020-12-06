# ---------------------------------------------------------------------------- #

from __future__ import annotations

import json
import pathlib
import setuptools
import setuptools.command.build_py
import setuptools.command.develop
import setuptools.command.sdist
import subprocess
import typing

# ---------------------------------------------------------------------------- #


class CustomBuildPyCommand(setuptools.command.build_py.build_py):
    def run(self) -> None:
        if pathlib.Path("truffle").exists():
            generate_contract_module()
        super().run()


class CustomDevelopCommand(setuptools.command.develop.develop):
    def run(self) -> None:
        generate_contract_module()
        super().run()


class CustomSdistCommand(setuptools.command.sdist.sdist):
    def run(self) -> None:
        generate_contract_module()
        super().run()


def generate_contract_module() -> None:

    # install dependencies

    subprocess.run(["npm", "install"], cwd="truffle", check=True)

    # compile contracts

    subprocess.run(
        ["node", "node_modules/truffle/build/cli.bundled.js", "compile"],
        cwd="truffle",
        check=True,
    )

    # generate module

    with open("tuichain/_contracts.py", mode="w") as f:

        f.write("import typing as _t\n")

        add_contract(f, "TuiChainController", include_bytecode=True)
        add_contract(f, "TuiChainLoan")
        add_contract(f, "TuiChainMarket")
        add_contract(f, "TuiChainToken")


def add_contract(
    stream: typing.TextIO, contract: str, *, include_bytecode: bool = False
) -> None:

    with open(f"truffle/build/contracts/{contract}.json") as f:
        data = json.load(f)

    stream.write(f"class {contract}:\n")
    stream.write(f"    ABI: _t.ClassVar[_t.List[_t.Any]] = {data['abi']!r}\n")

    if include_bytecode:
        stream.write(f"    BYTECODE: str = {data['bytecode']!r}\n")


# ---------------------------------------------------------------------------- #

setuptools.setup(
    name="tuichain-ethereum",
    cmdclass={
        "build_py": CustomBuildPyCommand,
        "develop": CustomDevelopCommand,
        "sdist": CustomSdistCommand,
    },
    packages=setuptools.find_packages(include=["tuichain*"]),
    package_data={"tuichain": ["py.typed"]},  # as per PEP 561
    python_requires="~=3.8",
    install_requires=["web3~=5.13"],
    extras_require={
        "test": ["black", "mypy", "pytest", "tox", "web3[tester]~=5.13"]
    },
    include_package_data=True,
    zip_safe=False,  # for compatibility with mypy
)

# ---------------------------------------------------------------------------- #
