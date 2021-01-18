# ---------------------------------------------------------------------------- #

from __future__ import annotations

import dataclasses as _dataclasses
import datetime as _datetime
import enum as _enum
import functools as _functools
import math as _math
import typing as _t

import eth_utils as _eth_utils
import web3 as _web3
import web3.contract as _web3_contract
import web3.logs as _web3_logs
import web3.types as _web3_types

import tuichain_ethereum._contracts as _tuichain_contracts

from tuichain_ethereum._controller import *

# ---------------------------------------------------------------------------- #


class LoanIdentifier:
    """
    Identifies a loan.

    Instances of this type are equality comparable and hashable.
    """

    @classmethod
    def _random(cls) -> LoanIdentifier:
        """(private, do not use)"""
        return LoanIdentifier(str(Address._random()))

    __address: _web3_types.ChecksumAddress

    def __init__(self, identifier: str) -> None:
        """
        Initialize a loan identifier from its string representation.

        :param identifier: the loan identifier's string representation

        :raise ValueError: if ``identifier`` is not a valid loan identifier
        """

        assert isinstance(identifier, str)

        if not _web3.Web3.isAddress(identifier):
            raise ValueError(f"Invalid loan identifier {identifier!r}")

        if not _web3.Web3.isChecksumAddress(identifier):
            raise ValueError(f"Invalid loan identifier {identifier!r}")

        self.__address = _web3.Web3.toChecksumAddress(identifier)

        if str(self.__address) == "0x0000000000000000000000000000000000000000":
            raise ValueError(f"Invalid loan identifier {identifier!r}")

    def __str__(self) -> str:
        """Return this loan identifier's string representation, which is always
        42 ASCII alphanumeric characters long."""
        return str(self.__address)

    def __eq__(self, other: _t.Any) -> bool:
        return (
            type(other) is LoanIdentifier and self.__address == other.__address
        )

    def __hash__(self) -> int:
        return hash(self.__address)

    def __repr__(self) -> str:
        return f"LoanIdentifier({str(self.__address)!r})"

    @property
    def _checksummed(self) -> _web3_types.ChecksumAddress:
        """(private, do not use)"""
        return self.__address


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


class LoanState:
    """Holds a snapshot of a loan's mutable state."""

    __caller: _web3_contract.ContractCaller

    def __init__(self, caller: _web3_contract.ContractCaller) -> None:
        """(private, do not use)"""
        self.__caller = caller

    @_functools.cached_property
    def phase(self) -> LoanPhase:
        """Current loan phase."""
        return LoanPhase(int(self.__caller.phase()))

    @_functools.cached_property
    def funded_value_atto_dai(self) -> int:
        """
        Loan value funded so far (excluding fees), in atto-Dai.

        Equals the request value if phase is ACTIVE or FINALIZED.
        """
        return int(self.__caller.fundedValueAttoDai())

    @_functools.cached_property
    def paid_value_atto_dai(self) -> _t.Optional[int]:
        """
        Total value paid so far (excluding fees), in atto-Dai.

        Is None if phase is not ACTIVE or FINALIZED.
        """
        return (
            int(self.__caller.paidValueAttoDai())
            if self.phase in [LoanPhase.ACTIVE, LoanPhase.FINALIZED]
            else None
        )

    @_functools.cached_property
    def redemption_value_atto_dai_per_token(self) -> _t.Optional[int]:
        """
        How much atto-Dai each token can be redeemed for.

        Is None if phase is not FINALIZED.
        """
        return (
            int(self.__caller.redemptionValueAttoDaiPerToken())
            if self.phase == LoanPhase.FINALIZED
            else None
        )


# ---------------------------------------------------------------------------- #


def _wrong_phase_error(
    observed: LoanPhase, allowed: _t.Iterable[LoanPhase]
) -> ValueError:
    """(private, do not use)"""

    allowed_set = frozenset(allowed)

    assert allowed_set
    assert observed not in allowed_set

    sorted_allowed = sorted(allowed_set, key=lambda p: int(p.value))

    return ValueError(
        f"Loan is in phase {observed.name}, expected"
        f" {', '.join(p.name for p in sorted_allowed)}"
    )


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
                identifier=LoanIdentifier(caller.loans(i)),
            )

    def get_by_recipient(self, recipient_address: Address) -> _t.Iterable[Loan]:
        """
        Return an iterable over all loans with the given recipient address, in
        order of creation.

        The iterable always provides a consistent snapshot of the set of
        existing loans, no matter how slowly it is iterated over.
        """

        assert isinstance(recipient_address, Address)

        return (
            loan
            for loan in self.get_all()
            if loan.recipient_address == recipient_address
        )

    def get_by_token_holder(self, holder: Address) -> _t.Iterable[Loan]:
        """
        Return an iterable over all loans whose token the account with the given
        address has a positive balance of, in order of creation.

        The iterable always provides a consistent snapshot of the set of
        existing loans, no matter how slowly it is iterated over.
        """

        assert isinstance(holder, Address)

        return (
            loan
            for loan in self.get_all()
            if loan.get_token_balance_of(holder) > 0
        )

    def get_by_identifier(self, identifier: LoanIdentifier) -> Loan:
        """
        Return the loan with the given identifier.

        :raise ValueError: if no such loan exists
        """

        assert isinstance(identifier, LoanIdentifier)

        if not self.__controller._contract.caller.loanIsValid(str(identifier)):
            raise ValueError(f"No loan with identifier {identifier}")

        return Loan(controller=self.__controller, identifier=identifier)

    def create(
        self,
        recipient_address: Address,
        time_to_expiration: _datetime.timedelta,
        *,
        funding_fee_atto_dai_per_dai: int,
        payment_fee_atto_dai_per_dai: int,
        requested_value_atto_dai: int,
    ) -> Transaction[Loan]:
        """
        Create a loan.

        Currency parameters are keyword-only to prevent mistakes.

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

        if time_to_expiration <= _datetime.timedelta():
            raise ValueError("`time_to_expiration` must be positive")

        if funding_fee_atto_dai_per_dai < 0:
            raise ValueError(
                "`funding_fee_atto_dai_per_dai` must not be negative"
            )

        if payment_fee_atto_dai_per_dai < 0:
            raise ValueError(
                "`payment_fee_atto_dai_per_dai` must not be negative"
            )

        if (
            requested_value_atto_dai <= 0
            or requested_value_atto_dai % (10 ** 18) != 0
        ):
            raise ValueError(
                "`requested_value_atto_dai` must be a positive multiple of 1"
                " Dai"
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
                identifier=LoanIdentifier(events[0].args.loan),
            )

        return Transaction._real(
            w3=self.__controller._w3, tx_hash=tx_hash, on_success=on_success
        )

    def __eq__(self, other: _t.Any) -> bool:
        raise NotImplementedError

    def __hash__(self) -> int:
        raise NotImplementedError


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
        self, controller: Controller, identifier: LoanIdentifier
    ) -> None:
        """(private, do not use)"""
        self.__controller = controller
        self.__identifier = identifier

    @property
    def _controller(self) -> Controller:
        """(private, do not use)"""
        return self.__controller

    @_functools.cached_property
    def _contract(self) -> _web3_contract.Contract:
        """(private, do not use)"""
        return self.__controller._loan_contract_factory(
            address=self.__identifier._checksummed
        )

    @_functools.cached_property
    def _token_contract(self) -> _web3_contract.Contract:
        """(private, do not use)"""
        return self.__controller._token_contract_factory(
            address=_eth_utils.to_checksum_address(
                self._contract.caller.token()
            ),
        )

    @_functools.cached_property
    def user_transaction_builder(self) -> LoanUserTransactionBuilder:
        """The user transaction builder for the loan."""
        return LoanUserTransactionBuilder(loan=self)

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
        Return a consistent snapshot of the loan's mutable state.

        :return: a consistent snapshot of the loan's mutable state
        """

        # get caller referencing specific block to ensure consistent snapshot

        caller = self._contract.caller(
            block_identifier=self.__controller._w3.eth.blockNumber
        )

        # return loan state

        return LoanState(caller)

    def get_token_balance_of(self, account: Address) -> int:
        """
        Return the amount of this loan's tokens that the account with the given
        address is currently holding.

        :param account: the address of the account whose balance to return

        :return: the balance of the account with the given address, in number of
            tokens of this loan
        """

        assert isinstance(account, Address)

        return int(self._token_contract.caller.balanceOf(account._checksummed))

    def try_expire(self) -> Transaction[bool]:
        """
        Expire the loan if its funding deadline has passed.

        This function is necessary since the loan contract must be interacted
        with for it to notice that it expired and transition to phase EXPIRED
        accordingly.

        Note that a loan may nevertheless become expired without this function
        ever being called if users interact with it.

        The resulting transaction fails if the loan is not in phase FUNDING or
        EXPIRED.

        This action may use up some ether from the master account.

        :return: the corresponding transaction, whose result is ``True`` if the
            loan became or already was expired, and ``False`` otherwise
        """

        # NOTE: This function avoids spending ether unless it can be certain
        # that the loan would transition from phase FUNDING to EXPIRED. This
        # makes it unable to expire a loan in the earliest block that it could
        # expire in, but that shouldn't be a big deal.

        # get latest block once to ensure consistent snapshot

        block = self.__controller._w3.eth.get_block("latest")

        # get loan and its phase

        caller = self._contract.caller(block_identifier=block["number"])

        phase = LoanPhase(int(caller.phase()))

        # decide what to do

        if phase not in [LoanPhase.FUNDING, LoanPhase.EXPIRED]:

            # wrong loan phase

            return Transaction._fake_failed(
                error=_wrong_phase_error(
                    observed=phase,
                    allowed=[LoanPhase.FUNDING, LoanPhase.EXPIRED],
                )
            )

        elif phase == LoanPhase.EXPIRED:

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

        The resulting transaction fails if the loan is not in phase FUNDING.

        This action may use up some ether from the master account.

        :return: the corresponding transaction
        """

        return self._cancel_or_finalize("cancelLoan", LoanPhase.FUNDING)

    def finalize(self) -> Transaction[None]:
        """
        Finalize the loan.

        The resulting transaction fails if the loan is not in phase ACTIVE.

        This action may use up some ether from the master account.

        :return: the corresponding transaction
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
                error=_wrong_phase_error(
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
                raise _wrong_phase_error(
                    observed=new_phase, allowed=[allowed_phase]
                )

        return Transaction._real(
            w3=self.__controller._w3,
            tx_hash=tx_hash,
            on_success=lambda _: None,
            on_failure=on_failure,
        )

    def __eq__(self, other: _t.Any) -> bool:
        raise NotImplementedError

    def __hash__(self) -> int:
        raise NotImplementedError


# ---------------------------------------------------------------------------- #


class LoanUserTransactionBuilder:
    """Provides functionality to build transactions for users to interact with a
    loan contract."""

    __loan: Loan

    def __init__(self, loan: Loan) -> None:
        """(private, do not use)"""
        self.__loan = loan

    def provide_funds(
        self, *, value_atto_dai: int
    ) -> _t.Sequence[UserTransaction]:
        """
        Build a sequence of transactions for a user to provide funds to the
        loan.

        Currency parameters are keyword-only to prevent mistakes regarding
        units.

        :param value_atto_dai: the value to provide, in atto-Dai

        :return: the sequence of transactions to be submitted by the user

        :raise ValueError: if ``value_atto_dai`` is not a positive multiple of 1
            Dai
        :raise ValueError: if the loan is not in phase FUNDING
        """

        # validate arguments and state

        assert isinstance(value_atto_dai, int)

        if value_atto_dai <= 0 or value_atto_dai % (10 ** 18) != 0:
            raise ValueError(
                "`value_atto_dai` must be a positive multiple of 1 Dai"
            )

        if (p := self.__loan.get_state().phase) != LoanPhase.FUNDING:
            raise _wrong_phase_error(observed=p, allowed=[LoanPhase.FUNDING])

        # build and return transactions

        fee = self.__loan.funding_fee_atto_dai_per_dai
        total_value = value_atto_dai + fee * (value_atto_dai // (10 ** 18))

        return UserTransaction._build_sequence(
            # set Dai allowance for User --> Loan transfer
            self.__loan._controller._dai_contract.functions.approve(
                spender=self.__loan._contract.address,
                amount=total_value,
            ),
            # provide funds to loan contract, obtaining tokens
            self.__loan._contract.functions.provideFunds(
                _valueAttoDai=value_atto_dai
            ),
        )

    def withdraw_funds(
        self, *, value_atto_dai: int
    ) -> _t.Sequence[UserTransaction]:
        """
        Build a sequence of transactions for a user to withdraw funds previously
        provided to the loan.

        Currency parameters are keyword-only to prevent mistakes regarding
        units.

        :param value_atto_dai: the value to withdraw, in atto-Dai

        :return: the sequence of transactions to be submitted by the user

        :raise ValueError: if ``value_atto_dai`` is not a positive multiple of 1
            Dai
        :raise ValueError: if the loan is not in phase FUNDING
        """

        # validate arguments and state

        assert isinstance(value_atto_dai, int)

        if value_atto_dai <= 0 or value_atto_dai % (10 ** 18) != 0:
            raise ValueError(
                "`value_atto_dai` must be a positive multiple of 1 Dai"
            )

        if (p := self.__loan.get_state().phase) != LoanPhase.FUNDING:
            raise _wrong_phase_error(observed=p, allowed=[LoanPhase.FUNDING])

        # build and return transactions

        amount_tokens = value_atto_dai // (10 ** 18)

        return UserTransaction._build_sequence(
            # set token allowance for User --> Loan transfer
            self.__loan._token_contract.functions.approve(
                spender=self.__loan._contract.address,
                amount=amount_tokens,
            ),
            # withdraw funds from loan contract, returning tokens
            self.__loan._contract.functions.withdrawFunds(
                _valueAttoDai=value_atto_dai
            ),
        )

    def make_payment(
        self, *, value_atto_dai: int
    ) -> _t.Sequence[UserTransaction]:
        """
        Build a sequence of transactions for a user to make a payment to the
        loan.

        Currency parameters are keyword-only to prevent mistakes regarding
        units.

        :param value_atto_dai: the payment's value, in atto-Dai

        :return: the sequence of transactions to be submitted by the user

        :raise ValueError: if ``value_atto_dai`` is not a positive multiple of 1
            Dai
        :raise ValueError: if the loan is not in phase ACTIVE
        """

        # validate arguments and state

        assert isinstance(value_atto_dai, int)

        if value_atto_dai <= 0 or value_atto_dai % (10 ** 18) != 0:
            raise ValueError(
                "`value_atto_dai` must be a positive multiple of 1 Dai"
            )

        if (p := self.__loan.get_state().phase) != LoanPhase.ACTIVE:
            raise _wrong_phase_error(observed=p, allowed=[LoanPhase.ACTIVE])

        # build and return transactions

        fee = self.__loan.payment_fee_atto_dai_per_dai
        total_value = value_atto_dai + fee * (value_atto_dai // (10 ** 18))

        return UserTransaction._build_sequence(
            # set Dai allowance for User --> Loan transfer
            self.__loan._controller._dai_contract.functions.approve(
                spender=self.__loan._contract.address,
                amount=total_value,
            ),
            # make payment
            self.__loan._contract.functions.makePayment(
                _valueAttoDai=value_atto_dai
            ),
        )

    def redeem_tokens(self, amount_tokens: int) -> _t.Sequence[UserTransaction]:
        """
        Build a sequence of transactions for a user to redeem tokens previously
        obtained by funding the loan.

        :param amount_tokens: the number of tokens to redeem

        :return: the sequence of transactions to be submitted by the user

        :raise ValueError: if ``amount_tokens`` is not positive
        :raise ValueError: if the loan is not in phase FINALIZED
        """

        # validate arguments and state

        assert isinstance(amount_tokens, int)

        if amount_tokens <= 0:
            raise ValueError("`amount_tokens` must be positive")

        if (p := self.__loan.get_state().phase) != LoanPhase.FINALIZED:
            raise _wrong_phase_error(observed=p, allowed=[LoanPhase.FINALIZED])

        # build and return transactions

        return UserTransaction._build_sequence(
            # set token allowance for User --> Loan transfer
            self.__loan._token_contract.functions.approve(
                spender=self.__loan._contract.address,
                amount=amount_tokens,
            ),
            # return tokens to loan contract, obtaining Dai
            self.__loan._contract.functions.redeemTokens(
                _amountTokens=amount_tokens
            ),
        )

    def __eq__(self, other: _t.Any) -> bool:
        raise NotImplementedError

    def __hash__(self) -> int:
        raise NotImplementedError


# ---------------------------------------------------------------------------- #
