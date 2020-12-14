# ---------------------------------------------------------------------------- #

from __future__ import annotations

import functools as _functools
import typing as _t

import web3 as _web3
import web3.contract as _web3_contract
import web3.providers as _web3_providers
import web3.types as _web3_types

import tuichain_ethereum._contracts as _tuichain_contracts
from tuichain_ethereum import *

# ---------------------------------------------------------------------------- #


class DaiMockContract:
    """(private, do not use)"""

    @classmethod
    def deploy(
        cls,
        provider: _web3_providers.BaseProvider,
        account_private_key: PrivateKey,
    ) -> Transaction[DaiMockContract]:
        """(private, do not use)"""

        assert isinstance(provider, _web3_providers.BaseProvider)
        assert isinstance(account_private_key, PrivateKey)

        w3 = _web3.Web3(provider=provider)
        w3.enable_strict_bytes_type_checking()

        contract = w3.eth.contract(
            abi=_tuichain_contracts.DaiMock.ABI,
            bytecode=_tuichain_contracts.DaiMock.BYTECODE,
        )

        tx_hash = account_private_key._transact(w3, contract.constructor())

        def on_success(receipt: _web3_types.TxReceipt) -> DaiMockContract:

            assert receipt["contractAddress"] is not None

            return DaiMockContract(
                provider=provider,
                account_private_key=account_private_key,
                contract_address=Address(receipt["contractAddress"]),
            )

        return Transaction._real(w3=w3, tx_hash=tx_hash, on_success=on_success)

    __w3: _web3.Web3
    __account: PrivateKey
    __contract: _web3_contract.Contract

    def __init__(
        self,
        provider: _web3_providers.BaseProvider,
        account_private_key: PrivateKey,
        contract_address: Address,
    ) -> None:
        """(private, do not use)"""

        assert isinstance(provider, _web3_providers.BaseProvider)
        assert isinstance(account_private_key, PrivateKey)
        assert isinstance(contract_address, Address)

        self.__w3 = _web3.Web3(provider=provider)
        self.__w3.enable_strict_bytes_type_checking()

        self.__w3.eth.defaultAccount = (
            account_private_key.address._checksummed  # type: ignore
        )

        self.__account = account_private_key

        self.__contract = self.__w3.eth.contract(
            address=contract_address._checksummed,
            abi=_tuichain_contracts.DaiMock.ABI,
        )

    @_functools.cached_property
    def address(self) -> Address:
        """(private, do not use)"""
        return Address(self.__contract.address)

    def mint(
        self, account_address: Address, atto_dai: int
    ) -> Transaction[None]:
        """(private, do not use)"""

        tx_hash = self.__account._transact(
            self.__w3,
            self.__contract.functions.mint(
                _account=account_address._checksummed,
                _amount=atto_dai,
            ),
        )

        return Transaction._real(
            w3=self.__w3, tx_hash=tx_hash, on_success=lambda _: None
        )

    def __eq__(self, other: _t.Any) -> bool:
        raise NotImplementedError

    def __hash__(self) -> int:
        raise NotImplementedError


# ---------------------------------------------------------------------------- #
