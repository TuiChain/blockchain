# ---------------------------------------------------------------------------- #

from __future__ import annotations

import dataclasses as _dataclasses
import datetime as _datetime
import enum as _enum
import functools as _functools
import math as _math
import typing as _t

import eth_utils as _eth_utils
import web3.contract as _web3_contract
import web3.logs as _web3_logs
import web3.types as _web3_types

import tuichain_ethereum._contracts as _tuichain_contracts

from tuichain_ethereum._controller import *

# ---------------------------------------------------------------------------- #


class LoanIdentifier:
    """
    Identifies a loan.

    Instances of this type are convertible to bytes, equality comparable, and
    hashable.
    """

    __identifier: bytes

    def __init__(self, identifier: bytes) -> None:
        """
        Initialize a loan identifier from its representation as a sequence of 20
        bytes.

        :param identifier: the loan identifier's representation

        :raise ValueError: if ``identifier`` is not 20 bytes in length
        :raise ValueError: if all bytes in ``identifier`` are zero
        """

        assert isinstance(identifier, bytes)

        if len(identifier) != 20:
            raise ValueError("`identifier` must be 32 bytes in length")

        if identifier == b"\0" * 20:
            raise ValueError("`identifier` must not be zero")

        self.__identifier = bytes(identifier)

    def __bytes__(self) -> bytes:
        """Return this loan identifier's representation as a sequence of 20
        bytes."""
        return self.__identifier

    def __eq__(self, other: _t.Any) -> bool:
        return (
            type(other) is LoanIdentifier
            and self.__identifier == other.__identifier
        )

    def __hash__(self) -> int:
        return hash(self.__identifier)

    def __repr__(self) -> str:
        return f"LoanIdentifier({self.__identifier!r})"


# ---------------------------------------------------------------------------- #


class LoanPhase(_enum.Enum):
    """Phases of a loan's life cycle."""

    # NOTE: These values must match those in TuiChainLoan.sol

    FUNDING = 0
    """Loan has not yet been fully funded. Lenders may deposit Dai."""

    EXPIRED = 1
    """Loan funding did not reach requested value prior to the deadline. Lenders
    may retrieve deposited Dai."""

    CANCELED = 2
    """Loan was canceled prior to be fully funded. Lenders may retrieve
    deposited Dai."""

    ACTIVE = 3
    """Loan was fully funded and tokens were distributed to lenders. Student is
    in debt, further payments may occur."""

    FINALIZED = 4
    """Student is exempt from any further payments. Token owners may redeem them
    for Dai."""


# ---------------------------------------------------------------------------- #


@_dataclasses.dataclass
class LoanState:
    """Holds a snapshot of a loan's mutable state."""

    phase: LoanPhase
    """Current loan phase."""

    funded_value_atto_dai: int
    """
    Loan value funded so far (excluding fees), in atto-Dai.

    Equals the request value if phase is ACTIVE or FINALIZED.
    """

    paid_value_atto_dai: _t.Optional[int]
    """
    Total value paid so far (excluding fees), in atto-Dai.

    Is None if phase is not ACTIVE or FINALIZED.
    """

    atto_dai_per_token: _t.Optional[int]
    """
    How much atto-Dai each token can be redeemed for.

    Is None if phase is not FINALIZED.
    """


# ---------------------------------------------------------------------------- #


class InvalidLoanPhaseError(ValueError):
    """An error caused by a loan not being in the expected phase."""

    __observed: LoanPhase
    __allowed: _t.AbstractSet[LoanPhase]

    def __init__(
        self, observed: LoanPhase, allowed: _t.Iterable[LoanPhase]
    ) -> None:
        """
        :param observed: the phase in which the loan was actually in
        :param allowed: phases in which the loan was allowed to be in
        """

        self.__observed = observed
        self.__allowed = frozenset(allowed)

        assert self.__allowed
        assert observed not in self.__allowed

        sorted_allowed = sorted(self.__allowed, key=lambda p: int(p.value))

        super().__init__(
            f"Loan is in phase {observed.name}, expected"
            f" {', '.join(p.name for p in sorted_allowed)}."
        )

    @property
    def observed(self) -> LoanPhase:
        """The phase in which the loan was observed to be."""
        return self.__observed

    @property
    def allowed(self) -> _t.AbstractSet[LoanPhase]:
        """The phases in which the loan was allowed to be."""
        return self.__allowed


# ---------------------------------------------------------------------------- #


class Loans:
    """A handle to a collection of loan contracts."""

    __controller: Controller

    def __init__(self, controller: Controller) -> None:
        """(private, do not use)"""
        self.__controller = controller

    def get_all(self) -> _t.Iterable[Loan]:
        """
        Return an iterable over all loans ever created, in order of creation.

        The iterable always provides a consistent snapshot of the set of
        existing loans, no matter how slowly it is iterated over.
        """

        # get caller referencing specific block to ensure consistent snapshot

        caller = self.__controller._contract.caller(
            block_identifier=self.__controller._w3.eth.blockNumber
        )

        # yield every loan

        for i in range(int(caller.numLoans())):

            yield Loan(
                controller=self.__controller,
                loan_contract_address=caller.loans(i),
            )

    def get_by_recipient(self, recipient_address: Address) -> _t.Iterable[Loan]:
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
            for loan in self.get_all()
            if loan.recipient_address == recipient_address
        )

    def get_by_identifier(
        self, identifier: LoanIdentifier
    ) -> _t.Optional[Loan]:
        """Return the loan with the given identifier, or ``None`` if no such
        loan exists."""

        assert isinstance(identifier, LoanIdentifier)

        if self.__controller._contract.caller.loanIsValid(bytes(identifier)):

            return Loan(
                controller=self.__controller,
                loan_contract_address=bytes(identifier),
            )

        else:

            return None

    def create(
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

        tx_hash = self.__controller._master_account._transact(
            self.__controller._w3,
            self.__controller._contract.functions.createLoan(
                _feeRecipient=(
                    self.__controller._master_account.address._checksummed
                ),
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
                self.__controller._contract.events.LoanCreated().processReceipt(
                    receipt, errors=_web3_logs.DISCARD
                )
            )

            assert len(events) == 1

            return Loan(
                controller=self.__controller,
                loan_contract_address=events[0].args.loan,
            )

        return Transaction._real(
            w3=self.__controller._w3, tx_hash=tx_hash, on_success=on_success
        )


# ---------------------------------------------------------------------------- #


class Loan:
    """
    A handle to a loan contract.

    Instances of this type are equality comparable and hashable. Two instances
    compare equal if and only if they refer to the same loan.
    """

    __controller: Controller
    __identifier: LoanIdentifier

    def __init__(
        self,
        controller: Controller,
        loan_contract_address: _t.AnyStr,
    ) -> None:
        """(private, do not use)"""

        self.__controller = controller

        self.__identifier = LoanIdentifier(
            _eth_utils.to_canonical_address(loan_contract_address)
        )

    @property
    def _controller(self) -> Controller:
        """(private, do not use)"""
        return self.__controller

    @_functools.cached_property
    def _contract(self) -> _web3_contract.Contract:
        """(private, do not use)"""
        return self.__controller._w3.eth.contract(
            address=_web3_types.Address(bytes(self.__identifier)),
            abi=_tuichain_contracts.TuiChainLoan.ABI,
        )

    @_functools.cached_property
    def _token_contract(self) -> _web3_contract.Contract:
        """(private, do not use)"""
        return self.__controller._w3.eth.contract(
            address=_eth_utils.to_checksum_address(
                self._contract.caller.token()
            ),
            abi=_tuichain_contracts.TuiChainToken.ABI,
        )

    @property
    def identifier(self) -> LoanIdentifier:
        """The loan's identifier."""
        return self.__identifier

    @_functools.cached_property
    def token_contract_address(self) -> Address:
        """Address of the contract implementing the loan's tokens."""
        return Address(self._token_contract.address)

    @_functools.cached_property
    def recipient_address(self) -> Address:
        """Address of account or contract to which the loaned funds are to be
        transferred."""
        return Address(self._contract.caller.loanRecipient())

    @_functools.cached_property
    def creation_time(self) -> _datetime.datetime:
        """Point in time at which the loan was created."""
        return _datetime.datetime.fromtimestamp(
            int(self._contract.caller.creationTime())
        )

    @_functools.cached_property
    def funding_expiration_time(self) -> _datetime.datetime:
        """Point in time at which the FUNDING phase is set to expire."""
        return _datetime.datetime.fromtimestamp(
            int(self._contract.caller.expirationTime())
        )

    @_functools.cached_property
    def funding_fee_atto_dai_per_dai(self) -> int:
        """Funding fee, in atto-Dai per Dai."""
        return int(self._contract.caller.fundingFeeAttoDaiPerDai())

    @_functools.cached_property
    def payment_fee_atto_dai_per_dai(self) -> int:
        """Payment fee, in atto-Dai per Dai."""
        return int(self._contract.caller.paymentFeeAttoDaiPerDai())

    @_functools.cached_property
    def requested_value_atto_dai(self) -> int:
        """Requested loan value, in atto-Dai."""
        return int(self._contract.caller.requestedValueAttoDai())

    def get_state(self) -> LoanState:
        """
        Return information about the loan's mutable state.

        Returns a consistent snapshot.

        :return: the loan's state
        """

        # get caller referencing specific block to ensure consistent snapshot

        caller = self._contract.caller(
            block_identifier=self.__controller._w3.eth.blockNumber
        )

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

        block = self.__controller._w3.eth.getBlock("latest")

        # get loan and its phase

        caller = self._contract.caller(block_identifier=block["number"])

        phase = LoanPhase(int(caller.phase()))

        # decide what to do

        if phase not in [LoanPhase.FUNDING, LoanPhase.EXPIRED]:

            # wrong loan phase

            return Transaction._fake_failed(
                error=InvalidLoanPhaseError(
                    observed=phase,
                    allowed=[LoanPhase.FUNDING, LoanPhase.EXPIRED],
                )
            )

        elif phase is LoanPhase.EXPIRED:

            # loan already expired, transaction unnecessary

            return Transaction._fake_successful(result=True)

        elif int(block["timestamp"]) >= int(caller.expirationTime()):

            # loan will expire, send transaction

            tx_hash = self.__controller._master_account._transact(
                self.__controller._w3,
                self._contract.functions.checkExpiration(),
            )

            def on_success(_: _web3_types.TxReceipt) -> bool:
                new_phase = LoanPhase(int(self._contract.caller.phase()))
                assert new_phase == LoanPhase.EXPIRED
                return True

            return Transaction._real(
                w3=self.__controller._w3, tx_hash=tx_hash, on_success=on_success
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

        phase = LoanPhase(int(self._contract.caller.phase()))

        if phase != allowed_phase:
            return Transaction._fake_failed(
                error=InvalidLoanPhaseError(
                    observed=phase, allowed=[allowed_phase]
                )
            )

        # send transaction

        function = getattr(self.__controller._contract.functions, function_name)

        tx_hash = self.__controller._master_account._transact(
            self.__controller._w3,
            function(_loan=self._contract.address),
        )

        # return transaction handle

        def on_failure(_: _web3_types.TxReceipt) -> None:

            new_phase = LoanPhase(int(self._contract.caller.phase()))

            if new_phase != allowed_phase:
                # may or may not have failed due to wrong phase, but will surely
                # fail due to wrong phase if retried
                raise InvalidLoanPhaseError(
                    observed=new_phase, allowed=[allowed_phase]
                )

        return Transaction._real(
            w3=self.__controller._w3,
            tx_hash=tx_hash,
            on_success=lambda _: None,
            on_failure=on_failure,
        )


# ---------------------------------------------------------------------------- #
