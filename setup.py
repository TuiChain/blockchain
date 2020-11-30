# ---------------------------------------------------------------------------- #

from __future__ import annotations

import json
import setuptools
import setuptools.command.egg_info
import subprocess

from pathlib import Path
from typing import Any, Dict, Iterable

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

    abi_dict: Dict[str, Any] = {}

    for path in Path(f"truffle/build/contracts").iterdir():
        with path.open() as f:
            abi_dict[path.stem] = json.load(f)["abi"]

    with Path(f"tuichain/abi.json").open(mode="w") as f:
        json.dump(abi_dict, f)


class CustomEggInfoCommand(setuptools.command.egg_info.egg_info):
    def run(self) -> None:
        compile_contracts()
        super().run()


# ---------------------------------------------------------------------------- #

setuptools.setup(
    name="tuichain-ethereum",
    cmdclass={"egg_info": CustomEggInfoCommand},
    packages=setuptools.find_packages(include=["tuichain*"]),
    package_data={"tuichain": ["abi.json", "py.typed"]},
    python_requires="~=3.8",
    install_requires=["web3~=5.13"],
    include_package_data=True,
    zip_safe=False,
)

# ---------------------------------------------------------------------------- #
