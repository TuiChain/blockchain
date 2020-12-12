# ---------------------------------------------------------------------------- #

from __future__ import annotations

import dataclasses as _dataclasses
import datetime as _datetime
import functools as _functools
import math as _math
import typing as _t

import eth_utils as _eth_utils
import web3 as _web3
import web3.contract as _web3_contract
import web3.logs as _web3_logs
import web3.providers as _web3_providers
import web3.types as _web3_types

import tuichain_ethereum._contracts as _tuichain_contracts
from tuichain_ethereum._base import *

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

        Make sure to specify the correct ``dai_contract_address`` for the chain
        you are deploying to. Constants :const:`Address.MAINNET_DAI_CONTRACT`
        and :const:`Address.ROPSTEN_TESTNET_DAI_CONTRACT` may be of use.

        This action may use up some ether from the master account.

        :param provider: specifies the Ethereum client to connect to
        :param master_account_private_key: the private key of the master account
        :param dai_contract_address: the address of the Dai contract to be used
        :param market_fee_atto_dai_per_nano_dai: the initial market fee, in
            atto-Dai per nano-Dai
        :return: a transaction whose result is a ``Controller`` instance
            connected to the deployed TuiChain controller contract

        :raise ValueError: if ``dai_contract_address`` is the zero address
        :raise ValueError: if ``market_fee_atto_dai_per_nano_dai`` is negative
        """

        # validate arguments

        assert isinstance(provider, _web3_providers.BaseProvider)
        assert isinstance(master_account_private_key, PrivateKey)
        assert isinstance(dai_contract_address, Address)
        assert isinstance(market_fee_atto_dai_per_nano_dai, int)

        if dai_contract_address == Address._ZERO:
            raise ValueError(
                "`dai_contract_address` must not be the zero address"
            )

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

    __controller: _web3_contract.Contract
    __market: Market

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

        self.__chain_id = int(self.__w3.eth.chainId)

        self.__master_account = master_account_private_key

        # get controller contracts

        self.__controller = self.__w3.eth.contract(
            address=contract_address._checksummed,
            abi=_tuichain_contracts.TuiChainController.ABI,
        )

        # ensure that master_account is the controller's owner

        if (
            Address(self.__controller.caller.owner())
            != master_account_private_key.address
        ):
            raise ValueError(
                "`master_account` is not the owner of `controller_contract`"
            )

        # create market handle

        self.__market = Market(
            w3=self.__w3,
            master_account_private_key=master_account_private_key,
            controller=self,
        )

    @property
    def chain_id(self) -> int:
        """
        The identifier of the Ethereum network the controller is deployed in.

        This can be used to distinguish between the Ethereum mainnet, Ropsten
        testnet, some local test network, etc.
        """
        return self.__chain_id

    @property
    def contract_address(self) -> Address:
        """The address of the controller contract."""
        return Address(self.__controller.address)

    @property
    def _contract(self) -> _web3_contract.Contract:
        """(private, do not use)"""
        return self.__controller

    @property
    def market(self) -> Market:
        """A handle to the market contract corresponding to this controller."""
        return self.__market

    def get_all_loans(self) -> _t.Iterable[Loan]:
        """
        Return an iterable over all loans ever created, in order of creation.

        The iterable always provides a consistent snapshot of the set of
        existing loans, no matter how slowly it is iterated over.
        """

        # get caller referencing specific block to ensure consistent snapshot

        caller = self.__controller.caller(
            block_identifier=self.__w3.eth.blockNumber
        )

        # yield every loan

        for i in range(int(caller.numLoans())):

            yield Loan(
                w3=self.__w3,
                master_account_private_key=self.__master_account,
                controller_contract=self.__controller,
                loan_contract_address=caller.loans(i),
            )

    def get_loans_by_recipient(
        self, recipient_address: Address
    ) -> _t.Iterable[Loan]:
        """
        Return an iterable over all loans with the given recipient address, in
        order of creation.

        The iterable always provides a consistent snapshot of the set of
        existing loans, no matter how slowly it is iterated over.
        """

        # TODO: implement properly

        assert isinstance(recipient_address, Address)

        return (
            loan
            for loan in self.get_all_loans()
            if loan.recipient_address == recipient_address
        )

    def get_loan_by_identifier(
        self, identifier: LoanIdentifier
    ) -> _t.Optional[Loan]:
        """Return the loan with the given identifier, or ``None`` if no such
        loan exists."""

        assert isinstance(identifier, LoanIdentifier)

        if self.__controller.caller.loanIsValid(bytes(identifier)):

            return Loan(
                w3=self.__w3,
                master_account_private_key=self.__master_account,
                controller_contract=self.__controller,
                loan_contract_address=bytes(identifier),
            )

        else:

            return None

    def create_loan(
        self,
        *,
        recipient_address: Address,
        time_to_expiration: _datetime.timedelta,
        funding_fee_atto_dai_per_dai: int,
        payment_fee_atto_dai_per_dai: int,
        requested_value_atto_dai: int,
    ) -> Transaction[Loan]:
        """
        Create a loan.

        Parameters are keyword-only to prevent mistakes.

        This action may use up some ether from the master account.

        :param recipient_address: address of account or contract to which the
            loaned funds are to be transferred
        :param time_to_expiration: maximum amount of time for loan to be fully
            funded
        :param funding_fee_atto_dai_per_dai: funding fee, in atto-Dai per Dai
        :param payment_fee_atto_dai_per_dai: payment fee, in atto-Dai per Dai.
        :param requested_value_atto_dai: requested loan value, in atto-Dai
        :return: the corresponding transaction, whose result is a handle to the
            created loan

        :raise ValueError: if ``recipient_address`` is the zero address
        :raise ValueError: if ``time_to_expiration`` is not positive
        :raise ValueError: if ``funding_fee_atto_dai_per_dai`` is negative
        :raise ValueError: if ``payment_fee_atto_dai_per_dai`` is negative
        :raise ValueError: if ``requested_value_atto_dai`` is not positive or
            not a multiple of 1 Dai
        """

        # validate arguments

        assert isinstance(recipient_address, Address)
        assert isinstance(time_to_expiration, _datetime.timedelta)
        assert isinstance(funding_fee_atto_dai_per_dai, int)
        assert isinstance(payment_fee_atto_dai_per_dai, int)
        assert isinstance(requested_value_atto_dai, int)

        if recipient_address == Address._ZERO:
            raise ValueError("recipient_address must not be the zero address")

        if time_to_expiration <= _datetime.timedelta():
            raise ValueError("time_to_expiration must be positive")

        if funding_fee_atto_dai_per_dai < 0:
            raise ValueError(
                "funding_fee_atto_dai_per_dai must not be negative"
            )

        if payment_fee_atto_dai_per_dai < 0:
            raise ValueError(
                "payment_fee_atto_dai_per_dai must not be negative"
            )

        if requested_value_atto_dai <= 0:
            raise ValueError("requested_value_atto_dai must be positive")

        if requested_value_atto_dai % (10 ** 18) != 0:
            raise ValueError(
                "requested_value_atto_dai must be a multiple of 1 Dai"
            )

        # send loan creation transaction

        tx_hash = self.__master_account._transact(
            self.__w3,
            self.__controller.functions.createLoan(
                _feeRecipient=self.__master_account.address._checksummed,
                _loanRecipient=recipient_address._checksummed,
                _secondsToExpiration=_math.ceil(
                    time_to_expiration.total_seconds()
                ),
                _fundingFeeAttoDaiPerDai=funding_fee_atto_dai_per_dai,
                _paymentFeeAttoDaiPerDai=payment_fee_atto_dai_per_dai,
                _requestedValueAttoDai=requested_value_atto_dai,
            ),
        )

        # return transaction handle

        def on_success(receipt: _web3_types.TxReceipt) -> Loan:

            events = tuple(
                self.__controller.events.LoanCreated().processReceipt(
                    receipt, errors=_web3_logs.DISCARD
                )
            )

            assert len(events) == 1

            return Loan(
                w3=self.__w3,
                master_account_private_key=self.__master_account,
                controller_contract=self.__controller,
                loan_contract_address=events[0].args.loan,
            )

        return Transaction._real(
            w3=self.__w3, tx_hash=tx_hash, on_success=on_success
        )


# ---------------------------------------------------------------------------- #


class Market:
    """A handle to a market contract."""

    __w3: _web3.Web3
    __master_account: PrivateKey

    __controller: Controller
    __market: _web3_contract.Contract

    def __init__(
        self,
        w3: _web3.Web3,
        master_account_private_key: PrivateKey,
        controller: Controller,
    ) -> None:
        """(private, do not use)"""

        self.__w3 = w3
        self.__master_account = master_account_private_key

        self.__controller = controller

        self.__market = w3.eth.contract(
            address=controller._contract.caller.market(),
            abi=_tuichain_contracts.TuiChainMarket.ABI,
        )

    def get_fee_atto_dai_per_nano_dai(self) -> int:
        """Return the current market purchase fee, in atto-Dai per nano-Dai."""
        return int(self.__market.caller.feeAttoDaiPerNanoDai())

    def set_fee(self, *, fee_atto_dai_per_nano_dai: int) -> Transaction[None]:
        """
        Set the market purchase fee.

        Parameter is keyword-only to prevent mistakes.

        This action may use up some ether from the master account.

        :param fee_atto_dai_per_nano_dai: the new market purchase fee, in
            atto-Dai per nano-Dai
        :return: the corresponding transaction

        :raise ValueError: if ``fee_atto_dai_per_nano_dai`` is negative
        """

        # validate argument

        assert isinstance(fee_atto_dai_per_nano_dai, int)

        if fee_atto_dai_per_nano_dai < 0:
            raise ValueError("fee_atto_dai_per_nano_dai must not be negative")

        # send transaction

        tx_hash = self.__master_account._transact(
            self.__w3,
            self.__controller._contract.functions.setMarketFee(
                _marketFeeAttoDaiPerNanoDai=fee_atto_dai_per_nano_dai
            ),
        )

        # return transaction handle

        return Transaction._real(
            w3=self.__w3, tx_hash=tx_hash, on_success=lambda _: None
        )

    def get_all_sell_positions(self) -> _t.Iterable[SellPosition]:
        """
        Return an iterable over all existing sell positions, in no particular
        order.

        The iterable always provides a consistent snapshot of the set of
        existing sell positions, no matter how slowly it is iterated over.
        """

        # get caller referencing specific block to ensure consistent snapshot

        caller = self.__market.caller(
            block_identifier=self.__w3.eth.blockNumber
        )

        # yield every sell position

        for i in range(int(caller.numSellPositions())):

            [
                token,
                seller,
                amount_tokens,
                price_atto_dai_per_token,
            ] = caller.sellPositionAt(i)

            token_contract = self.__w3.eth.contract(
                address=token,
                abi=_tuichain_contracts.TuiChainToken.ABI,
            )

            loan = Loan(
                w3=self.__w3,
                master_account_private_key=self.__master_account,
                controller_contract=self.__controller._contract,
                loan_contract_address=token_contract.caller.loan(),
            )

            yield SellPosition(
                loan=loan,
                seller_address=Address(seller),
                amount_tokens=int(amount_tokens),
                price_atto_dai_per_token=int(price_atto_dai_per_token),
            )

    def get_sell_positions_by_loan(
        self, loan: _t.Union[Loan, LoanIdentifier]
    ) -> _t.Iterable[SellPosition]:
        """
        Return an iterable over all existing sell positions offering tokens of
        the given loan, in no particular order.

        The iterable always provides a consistent snapshot of the set of
        existing sell positions, no matter how slowly it is iterated over.
        """

        # TODO: implement properly

        assert isinstance(loan, (Loan, LoanIdentifier))

        loan_identifier = loan.identifier if isinstance(loan, Loan) else loan

        return (
            position
            for position in self.get_all_sell_positions()
            if position.loan.identifier == loan_identifier
        )

    def get_sell_positions_by_seller(
        self, seller_address: Address
    ) -> _t.Iterable[SellPosition]:
        """
        Return an iterable over all existing sell positions whose seller has the
        given address, in no particular order.

        The iterable always provides a consistent snapshot of the set of
        existing sell positions, no matter how slowly it is iterated over.
        """

        # TODO: implement properly

        assert isinstance(seller_address, Address)

        return (
            position
            for position in self.get_all_sell_positions()
            if position.seller_address == seller_address
        )

    def get_sell_position_by_loan_and_seller(
        self, loan: _t.Union[Loan, LoanIdentifier], seller_address: Address
    ) -> _t.Optional[SellPosition]:
        """Return the sell position offering tokens of the given loan and whose
        seller has the given address, or ``None`` if no such sell position
        exists."""

        assert isinstance(loan, (Loan, LoanIdentifier))
        assert isinstance(seller_address, Address)

        if isinstance(loan, LoanIdentifier):

            actual_loan = self.__controller.get_loan_by_identifier(loan)

            if actual_loan is None:
                return None

            loan = actual_loan

        [
            amount_tokens,
            price_atto_dai_per_token,
        ] = self.__market.caller.getSellPosition(
            _token=loan._token_contract_address,
            _seller=seller_address._checksummed,
        )

        return SellPosition(
            loan=loan,
            seller_address=seller_address,
            amount_tokens=int(amount_tokens),
            price_atto_dai_per_token=int(price_atto_dai_per_token),
        )


# ---------------------------------------------------------------------------- #


@_dataclasses.dataclass
class SellPosition:
    """Represents the state of a sell position."""

    loan: Loan
    """The loan to which the tokens being sold pertain to."""

    seller_address: Address
    """The address of the account or contract selling the tokens."""

    amount_tokens: int
    """How many tokens are up for sale."""

    price_atto_dai_per_token: int
    """The token sell price, in atto-Dai per token."""


# ---------------------------------------------------------------------------- #


class Loan:
    """
    A handle to a loan contract.

    Instances of this type are equality comparable and hashable. Two instances
    compare equal if and only if they refer to the same loan.
    """

    __w3: _web3.Web3
    __master_account: PrivateKey

    __controller: _web3_contract.Contract
    __identifier: LoanIdentifier

    def __init__(
        self,
        w3: _web3.Web3,
        master_account_private_key: PrivateKey,
        controller_contract: _web3_contract.Contract,
        loan_contract_address: _t.AnyStr,
    ) -> None:
        """(private, do not use)"""

        self.__w3 = w3
        self.__master_account = master_account_private_key

        self.__controller = controller_contract

        self.__identifier = LoanIdentifier(
            _eth_utils.to_canonical_address(loan_contract_address)
        )

    @_functools.cached_property
    def __loan(self) -> _web3_contract.Contract:
        """(private, do not use)"""
        return self.__w3.eth.contract(
            address=_web3_types.Address(bytes(self.__identifier)),
            abi=_tuichain_contracts.TuiChainLoan.ABI,
        )

    @_functools.cached_property
    def _token_contract_address(self) -> Address:
        """(private, do not use)"""
        return Address(self.__loan.caller.token())

    @property
    def identifier(self) -> LoanIdentifier:
        """The loan's identifier."""
        return self.__identifier

    @_functools.cached_property
    def recipient_address(self) -> Address:
        """Address of account or contract to which the loaned funds are to be
        transferred."""
        return Address(self.__loan.caller.loanRecipient())

    @_functools.cached_property
    def creation_time(self) -> _datetime.datetime:
        """Point in time at which the loan was created."""
        return _datetime.datetime.fromtimestamp(
            int(self.__loan.caller.creationTime())
        )

    @_functools.cached_property
    def funding_expiration_time(self) -> _datetime.datetime:
        """Point in time at which the FUNDING phase is set to expire."""
        return _datetime.datetime.fromtimestamp(
            int(self.__loan.caller.expirationTime())
        )

    @_functools.cached_property
    def funding_fee_atto_dai_per_dai(self) -> int:
        """Funding fee, in atto-Dai per Dai."""
        return int(self.__loan.caller.fundingFeeAttoDaiPerDai())

    @_functools.cached_property
    def payment_fee_atto_dai_per_dai(self) -> int:
        """Payment fee, in atto-Dai per Dai."""
        return int(self.__loan.caller.paymentFeeAttoDaiPerDai())

    @_functools.cached_property
    def requested_value_atto_dai(self) -> int:
        """Requested loan value, in atto-Dai."""
        return int(self.__loan.caller.requestedValueAttoDai())

    def get_state(self) -> LoanState:
        """
        Return information about the loan's mutable state.

        Returns a consistent snapshot.

        :return: the loan's state
        """

        # get caller referencing specific block to ensure consistent snapshot

        caller = self.__loan.caller(block_identifier=self.__w3.eth.blockNumber)

        # query and return loan state

        phase = LoanPhase(int(caller.phase()))

        return LoanState(
            phase=phase,
            funded_value_atto_dai=int(caller.fundedValueAttoDai()),
            paid_value_atto_dai=(
                int(caller.paidValueAttoDai())
                if phase in [LoanPhase.ACTIVE, LoanPhase.FINALIZED]
                else None
            ),
            atto_dai_per_token=(
                int(caller.redemptionValueAttoDaiPerToken())
                if phase is LoanPhase.FINALIZED
                else None
            ),
        )

    def try_expire(self) -> Transaction[bool]:
        """
        Expire the loan if its funding deadline has passed.

        This function is necessary since the loan contract must be interacted
        with for it to notice that it expired and transition to phase EXPIRED
        accordingly.

        Note that a loan may nevertheless become expired without this function
        ever being called if users interact with it.

        This action may use up some ether from the master account.

        :return: the corresponding transaction, whose result is ``True`` if the
            loan became or already was expired, and ``False`` otherwise

        :raise LoanPhaseError: if the loan is not in phase FUNDING or EXPIRED
        """

        # NOTE: This function avoids spending ether unless it can be certain
        # that the loan would transition from phase FUNDING to EXPIRED. This
        # makes it unable to expire a loan in the earliest block that it could
        # expire in, but that shouldn't be a big deal.

        # get latest block once to ensure consistent snapshot

        block = self.__w3.eth.getBlock("latest")

        # get loan and its phase

        caller = self.__loan.caller(block_identifier=block["number"])

        phase = LoanPhase(int(caller.phase()))

        # decide what to do

        if phase not in [LoanPhase.FUNDING, LoanPhase.EXPIRED]:

            # wrong loan phase

            return Transaction._fake_failed(
                error=WrongLoanPhaseError(
                    observed=phase,
                    allowed=[LoanPhase.FUNDING, LoanPhase.EXPIRED],
                )
            )

        elif phase is LoanPhase.EXPIRED:

            # loan already expired, transaction unnecessary

            return Transaction._fake_successful(result=True)

        elif int(block["timestamp"]) >= int(caller.expirationTime()):

            # loan will expire, send transaction

            tx_hash = self.__master_account._transact(
                self.__w3, self.__loan.functions.checkExpiration()
            )

            def on_success(_: _web3_types.TxReceipt) -> bool:
                new_phase = LoanPhase(int(self.__loan.caller.phase()))
                assert new_phase == LoanPhase.EXPIRED
                return True

            return Transaction._real(
                w3=self.__w3, tx_hash=tx_hash, on_success=on_success
            )

        else:

            # loan either would not expire or next block will be first in which
            # it can be expired, avoid transaction cost

            return Transaction._fake_successful(result=False)

    def cancel(self) -> Transaction[None]:
        """
        Cancel the loan.

        This action may use up some ether from the master account.

        :return: the corresponding transaction

        :raise LoanPhaseError: if the loan is not in phase FUNDING
        """

        return self._cancel_or_finalize("cancelLoan", LoanPhase.FUNDING)

    def finalize(self) -> Transaction[None]:
        """
        Finalize the loan.

        This action may use up some ether from the master account.

        :return: the corresponding transaction

        :raise LoanPhaseError: if the loan is not in phase ACTIVE
        """

        return self._cancel_or_finalize("finalizeLoan", LoanPhase.ACTIVE)

    def _cancel_or_finalize(
        self, function_name: str, allowed_phase: LoanPhase
    ) -> Transaction[None]:
        """(private, do not use)"""

        # check phase

        phase = LoanPhase(int(self.__loan.caller.phase()))

        if phase != allowed_phase:
            return Transaction._fake_failed(
                error=WrongLoanPhaseError(
                    observed=phase, allowed=[allowed_phase]
                )
            )

        # send transaction

        function = getattr(self.__controller.functions, function_name)

        tx_hash = self.__master_account._transact(
            self.__w3,
            function(_loan=self.__loan.address),
        )

        # return transaction handle

        def on_failure(_: _web3_types.TxReceipt) -> None:

            new_phase = LoanPhase(int(self.__loan.caller.phase()))

            if new_phase != allowed_phase:
                # may or may not have failed due to wrong phase, but will surely
                # fail due to wrong phase if retried
                raise WrongLoanPhaseError(
                    observed=new_phase, allowed=[allowed_phase]
                )

        return Transaction._real(
            w3=self.__w3,
            tx_hash=tx_hash,
            on_success=lambda _: None,
            on_failure=on_failure,
        )


# ---------------------------------------------------------------------------- #
