# ---------------------------------------------------------------------------- #

from __future__ import annotations

import functools as _functools
import typing as _t

import web3 as _web3
import web3.contract as _web3_contract
import web3.providers as _web3_providers
import web3.types as _web3_types

import tuichain_ethereum as _tuichain
import tuichain_ethereum._contracts as _tuichain_contracts

# ---------------------------------------------------------------------------- #


class DaiMockContract:
    """A handle to a Dai mock contract, which provides a standard ERC-20
    interface and functionality to mint arbitrary amounts of Dai."""

    @classmethod
    def deploy(
        cls,
        provider: _web3_providers.BaseProvider,
        account_private_key: _tuichain.PrivateKey,
    ) -> _tuichain.Transaction[DaiMockContract]:
        """
        Deploy an instance of a Dai mock contract.

        :param provider: specifies the Ethereum client to connect to
        :param account_private_key: the private key of the account to deploy the
            contract with

        :return: a transaction whose result is a ``DaiMockContract`` instance
            connected to the deployed Dai mock contract
        """

        # validate arguments

        assert isinstance(provider, _web3_providers.BaseProvider)
        assert isinstance(account_private_key, _tuichain.PrivateKey)

        # send transaction

        w3 = _web3.Web3(provider=provider)
        w3.enable_strict_bytes_type_checking()

        contract = w3.eth.contract(
            abi=_tuichain_contracts.DaiMock.ABI,
            bytecode=_tuichain_contracts.DaiMock.BYTECODE,
        )

        tx_hash = account_private_key._transact(w3, contract.constructor())

        # return transaction handle

        def on_success(receipt: _web3_types.TxReceipt) -> DaiMockContract:

            assert receipt["contractAddress"] is not None

            return DaiMockContract(
                provider=provider,
                contract_address=_tuichain.Address(receipt["contractAddress"]),
            )

        return _tuichain.Transaction._real(
            w3=w3, tx_hash=tx_hash, on_success=on_success
        )

    __w3: _web3.Web3
    __contract: _web3_contract.Contract

    def __init__(
        self,
        provider: _web3_providers.BaseProvider,
        contract_address: _tuichain.Address,
    ) -> None:
        """
        Connect to a deployed Dai mock contract.

        :param provider: specifies the Ethereum client to connect to
        :param contract_address: the address of the Dai mock contract
        """

        # validate arguments

        assert isinstance(provider, _web3_providers.BaseProvider)
        assert isinstance(contract_address, _tuichain.Address)

        # initialize Web3 instance

        self.__w3 = _web3.Web3(provider=provider)
        self.__w3.enable_strict_bytes_type_checking()

        # get contract instance

        self.__contract = self.__w3.eth.contract(
            address=contract_address._checksummed,
            abi=_tuichain_contracts.DaiMock.ABI,
        )

    @_functools.cached_property
    def address(self) -> _tuichain.Address:
        """The address of the Dai mock contract."""
        return _tuichain.Address(self.__contract.address)

    def mint(
        self, account_private_key: _tuichain.PrivateKey, atto_dai: int
    ) -> _tuichain.Transaction[None]:
        """
        Mint the given amount of Dai.

        :param account_private_key: the private key of the account from which to
            send the resulting transaction and to which to transfer the minted
            funds
        :param atto_dai: the amount of funds to mint, in atto-Dai

        :return: the resulting transaction
        """

        tx_hash = account_private_key._transact(
            self.__w3,
            self.__contract.functions.mint(
                _account=account_private_key.address._checksummed,
                _amount=atto_dai,
            ),
        )

        return _tuichain.Transaction._real(
            w3=self.__w3, tx_hash=tx_hash, on_success=lambda _: None
        )

    def __eq__(self, other: _t.Any) -> bool:
        raise NotImplementedError

    def __hash__(self) -> int:
        raise NotImplementedError


# ---------------------------------------------------------------------------- #
