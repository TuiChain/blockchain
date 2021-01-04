# ---------------------------------------------------------------------------- #

from __future__ import annotations

import functools as _functools
import typing as _t

import web3 as _web3
import web3.contract as _web3_contract
import web3.providers as _web3_providers
import web3.types as _web3_types

import tuichain_ethereum._contracts as _tuichain_contracts

from tuichain_ethereum._base import *
from tuichain_ethereum._loans import Loans
from tuichain_ethereum._market import Market

# ---------------------------------------------------------------------------- #


class Controller:
    """A handle to a controller contract."""

    @classmethod
    def deploy(
        cls,
        provider: _web3_providers.BaseProvider,
        master_account_private_key: PrivateKey,
        dai_contract_address: Address,
        market_fee_atto_dai_per_nano_dai: int,
    ) -> Transaction[Controller]:
        """
        Deploy an instance of the TuiChain Ethereum infrastructure.

        The ``provider`` specifies the Ethereum client to connect to. Examples:

        - ``web3.IPCProvider('./path/to/geth.ipc')``
        - ``web3.HTTPProvider('http://127.0.0.1:8545')``
        - ``web3.WebsocketProvider('ws://127.0.0.1:8546')``

        The ``master_account_private_key`` is currently used for everything,
        from signing and paying transactions to receiving funds.

        This action may use up some ether from the master account.

        :param provider: specifies the Ethereum client to connect to
        :param master_account_private_key: the private key of the master account
        :param dai_contract_address: the address of the Dai contract to be used
        :param market_fee_atto_dai_per_nano_dai: the initial market fee, in
            atto-Dai per nano-Dai

        :return: a transaction whose result is a ``Controller`` instance
            connected to the deployed TuiChain controller contract

        :raise ValueError: if ``market_fee_atto_dai_per_nano_dai`` is negative
        """

        # validate arguments

        assert isinstance(provider, _web3_providers.BaseProvider)
        assert isinstance(master_account_private_key, PrivateKey)
        assert isinstance(dai_contract_address, Address)
        assert isinstance(market_fee_atto_dai_per_nano_dai, int)

        if market_fee_atto_dai_per_nano_dai < 0:
            raise ValueError("`fee_atto_dai_per_nano_dai` must not be negative")

        # send transaction

        w3 = _web3.Web3(provider=provider)
        w3.enable_strict_bytes_type_checking()

        controller = w3.eth.contract(
            abi=_tuichain_contracts.TuiChainController.ABI,
            bytecode=_tuichain_contracts.TuiChainController.BYTECODE,
        )

        tx_hash = master_account_private_key._transact(
            w3,
            controller.constructor(
                _dai=dai_contract_address._checksummed,
                _marketFeeRecipient=(
                    master_account_private_key.address._checksummed
                ),
                _marketFeeAttoDaiPerNanoDai=market_fee_atto_dai_per_nano_dai,
            ),
        )

        # return transaction handle

        def on_success(receipt: _web3_types.TxReceipt) -> Controller:

            assert receipt["contractAddress"] is not None

            return Controller(
                provider=provider,
                master_account_private_key=master_account_private_key,
                contract_address=Address(receipt["contractAddress"]),
            )

        return Transaction._real(w3=w3, tx_hash=tx_hash, on_success=on_success)

    __w3: _web3.Web3
    __chain_id: int
    __master_account: PrivateKey

    __contract: _web3_contract.Contract
    __dai_contract: _web3_contract.Contract

    def __init__(
        self,
        provider: _web3_providers.BaseProvider,
        master_account_private_key: PrivateKey,
        contract_address: Address,
    ) -> None:
        """
        Connect to a deployed controller contract.

        The ``provider`` specifies the Ethereum client to connect to. Examples:

        - ``web3.IPCProvider('./path/to/geth.ipc')``
        - ``web3.HTTPProvider('http://127.0.0.1:8545')``
        - ``web3.WebsocketProvider('ws://127.0.0.1:8546')``

        The ``master_account_private_key`` is currently used for everything,
        from signing and paying transactions to receiving funds.

        :param provider: specifies the Ethereum client to connect to
        :param master_account_private_key: the private key of the master account
        :param contract_address: the address of the controller contract

        :raise ValueError: if ``master_account_private_key`` is not the owner of
            the controller contract at ``contract_address``
        """

        # validate arguments

        assert isinstance(provider, _web3_providers.BaseProvider)
        assert isinstance(master_account_private_key, PrivateKey)
        assert isinstance(contract_address, Address)

        # initialize Web3 instance

        self.__w3 = _web3.Web3(provider=provider)
        self.__w3.enable_strict_bytes_type_checking()

        self.__w3.eth.defaultAccount = (
            master_account_private_key.address._checksummed  # type: ignore
        )

        # store chain identifier and master account

        self.__chain_id = int(self.__w3.eth.chainId)

        self.__master_account = master_account_private_key

        # get controller and Dai contracts

        self.__contract = self.__w3.eth.contract(
            address=contract_address._checksummed,
            abi=_tuichain_contracts.TuiChainController.ABI,
        )

        self.__dai_contract = self.__w3.eth.contract(
            address=self.__contract.caller.dai(),
            abi=_tuichain_contracts.IERC20.ABI,
        )

        # ensure that master_account is the controller's owner

        owner = Address(self.__contract.caller.owner())

        if owner != master_account_private_key.address:
            raise ValueError(
                "`master_account` is not the owner of `controller_contract`"
            )

    @property
    def _w3(self) -> _web3.Web3:
        """(private, do not use)"""
        return self.__w3

    @property
    def _master_account(self) -> PrivateKey:
        """(private, do not use)"""
        return self.__master_account

    @property
    def _contract(self) -> _web3_contract.Contract:
        """(private, do not use)"""
        return self.__contract

    @property
    def _dai_contract(self) -> _web3_contract.Contract:
        """(private, do not use)"""
        return self.__dai_contract

    @property
    def chain_id(self) -> int:
        """
        The identifier of the Ethereum network the controller is deployed in.

        This can be used to distinguish between the Ethereum mainnet, Ropsten
        testnet, some local test network, etc.
        """
        return self.__chain_id

    @_functools.cached_property
    def contract_address(self) -> Address:
        """The address of the controller contract."""
        return Address(self.__contract.address)

    @_functools.cached_property
    def loans(self) -> Loans:
        """A handle to the collection of loan contracts managed by this
        controller."""

        from tuichain_ethereum._loans import Loans

        return Loans(controller=self)

    @_functools.cached_property
    def market(self) -> Market:
        """A handle to the market contract corresponding to this controller."""

        from tuichain_ethereum._market import Market

        return Market(controller=self)

    def __eq__(self, other: _t.Any) -> bool:
        raise NotImplementedError

    def __hash__(self) -> int:
        raise NotImplementedError


# ---------------------------------------------------------------------------- #
