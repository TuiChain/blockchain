# ---------------------------------------------------------------------------- #

from __future__ import annotations

import json
import pathlib
import setuptools
import setuptools.command.develop
import setuptools.command.install
import setuptools.command.sdist
import subprocess

# ---------------------------------------------------------------------------- #


def compile_contracts() -> None:

    # install dependencies

    subprocess.run(["npm", "install"], cwd="truffle", check=True)

    # compile contracts

    subprocess.run(
        ["node", "node_modules/truffle/build/cli.bundled.js", "compile"],
        cwd="truffle",
        check=True,
    )

    # store contract ABIs as package data

    abi_dict = {}

    for path in pathlib.Path("truffle/build/contracts").iterdir():
        with path.open() as f:
            abi_dict[path.stem] = json.load(f)["abi"]

    with pathlib.Path("tuichain/abi.json").open(mode="w") as f:
        json.dump(abi_dict, f)


class CustomDevelopCommand(setuptools.command.develop.develop):
    def run(self) -> None:
        compile_contracts()
        super().run()


class CustomInstallCommand(setuptools.command.install.install):
    def run(self) -> None:
        if pathlib.Path("truffle").exists():
            compile_contracts()
        super().run()


class CustomSdistCommand(setuptools.command.sdist.sdist):
    def run(self) -> None:
        compile_contracts()
        super().run()


# ---------------------------------------------------------------------------- #

setuptools.setup(
    name="tuichain-ethereum",
    cmdclass={
        "develop": CustomDevelopCommand,
        "install": CustomInstallCommand,
        "sdist": CustomSdistCommand,
    },
    packages=setuptools.find_packages(include=["tuichain*"]),
    package_data={"tuichain": ["abi.json", "py.typed"]},  # as per PEP 561
    python_requires="~=3.8",
    install_requires=["web3~=5.13"],
    extras_require={"test": ["web3[tester]~=5.13"]},
    include_package_data=True,
    zip_safe=False,  # for compatibility with mypy
)

# ---------------------------------------------------------------------------- #
