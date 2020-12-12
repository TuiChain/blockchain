# ---------------------------------------------------------------------------- #

from __future__ import annotations

import abc as _abc
import dataclasses as _dataclasses
import datetime as _datetime
import enum as _enum
import math as _math
import typing as _t

import web3 as _web3
import web3.contract as _web3_contract
import web3.exceptions as _web3_exceptions
import web3.middleware.signing as _web3_middleware_signing
import web3.types as _web3_types

# ---------------------------------------------------------------------------- #


class Address:
    """
    The address of an Ethereum account or contract.

    Instances of this type are equality comparable and hashable.
    """

    _ZERO: _t.ClassVar[Address]
    """(private, do not use)"""

    MAINNET_DAI_CONTRACT: _t.ClassVar[Address]
    """The address of the official Dai contract in the Ethereum mainnet."""

    ROPSTEN_TESTNET_DAI_CONTRACT: _t.ClassVar[Address]
    """The address of the official Dai contract in the Ropsten testnet."""

    __address: _web3_types.ChecksumAddress

    def __init__(self, address: str, *, validate_checksum: bool = True) -> None:
        """
        Initialize an address from its string representation.

        If ``validate_checksum`` is True, the given address string must be
        correctly checksummed as per ERC-55.

        :param address: a string representation of the address

        :raise ValueError: if ``address`` does not represent an address
        :raise ValueError: if ``validate_checksum`` is ``True`` and ``address``
            is not correctly checksummmed
        """

        assert isinstance(address, str)
        assert isinstance(validate_checksum, bool)

        if not _web3.Web3.isAddress(address):
            raise ValueError(f"Invalid address {address!r}")

        if validate_checksum and not _web3.Web3.isChecksumAddress(address):
            raise ValueError(f"Invalid checksum in address {address!r}")

        self.__address = _web3.Web3.toChecksumAddress(address)

    def __str__(self) -> str:
        """Return this address' checksummed string representation."""
        return str(self.__address)

    def __eq__(self, other: _t.Any) -> bool:
        return type(other) is Address and self.__address == other.__address

    def __hash__(self) -> int:
        return hash(self.__address)

    def __repr__(self) -> str:
        return f"Address({str(self.__address)!r})"

    @property
    def _checksummed(self) -> _web3_types.ChecksumAddress:
        """(private, do not use)"""
        return self.__address


Address._ZERO = Address("0x0000000000000000000000000000000000000000")

Address.MAINNET_DAI_CONTRACT = Address(
    "0x6B175474E89094C44Da98b954EedeAC495271d0F"
)

Address.ROPSTEN_TESTNET_DAI_CONTRACT = Address(
    "0x31F42841c2db5173425b5223809CF3A38FEde360"
)

# ---------------------------------------------------------------------------- #


class PrivateKey:
    """
    The private key of an Ethereum account.

    Instances of this type are equality comparable and hashable.
    """

    __key: bytes
    __address: Address

    @classmethod
    def random(cls) -> PrivateKey:
        """Generate a random private key."""
        return PrivateKey(_web3.Account.create().key)

    def __init__(self, key: bytes) -> None:
        """
        Initialize a private key from its representation as a sequence of 32
        bytes.

        :param key: the key's representation

        :raise ValueError: if ``key`` is not 20 bytes in length
        :raise ValueError: if ``key`` does not represent a valid private key
        """

        assert isinstance(key, bytes)

        if len(key) != 32:
            raise ValueError("`key` must be 32 bytes in length")

        public_key = _web3_middleware_signing.PrivateKey(key).public_key

        self.__key = bytes(key)
        self.__address = Address(public_key.to_checksum_address())

    @property
    def address(self) -> Address:
        """The address corresponding to this private key."""
        return self.__address

    def __bytes__(self) -> bytes:
        """Return this private key's representation as a sequence of 32
        bytes."""
        return self.__key

    def __eq__(self, other: _t.Any) -> bool:
        return type(other) is PrivateKey and self.__key == other.__key

    def __hash__(self) -> int:
        return hash(self.__key)

    def __repr__(self) -> str:
        return f"PrivateKey({self.__key!r})"

    def _transact(
        self,
        w3: _web3.Web3,
        f: _t.Union[
            _web3_contract.ContractConstructor, _web3_contract.ContractFunction
        ],
    ) -> bytes:
        """(private, do not use)"""

        assert isinstance(
            f,
            (
                _web3_contract.ContractConstructor,
                _web3_contract.ContractFunction,
            ),
        )

        address = self.__address._checksummed
        nonce = w3.eth.getTransactionCount(address, "pending")

        params = f.buildTransaction({"from": address, "nonce": nonce})
        signed = _web3.Account.sign_transaction(params, self.__key)

        return w3.eth.sendRawTransaction(signed.rawTransaction)


# ---------------------------------------------------------------------------- #

T = _t.TypeVar("T")


class Transaction(_abc.ABC, _t.Generic[T]):
    """
    A handle to a transaction.

    ``Transaction`` objects are returned by functions that submit transactions
    to an Ethereum network, which may take a while to be confirmed and may also
    fail. ``Transaction`` objects allow you to check whether a transaction is
    pending confirmation, has been confirmed, or has failed.

    Transactions may also return a result. ``Transaction`` objects allow you to
    retrieve those results.
    """

    @_abc.abstractmethod
    def is_done(self) -> bool:
        """
        Whether the transaction is not pending confirmation, *i.e.*, has been
        confirmed or has failed.
        """

    @_abc.abstractmethod
    def get(
        self,
        *,
        timeout: _datetime.timedelta = _datetime.timedelta(minutes=2),
        poll_period: _datetime.timedelta = _datetime.timedelta(seconds=0.1),
    ) -> T:
        """
        Wait until the transaction is confirmed or fails and return its result
        or raise an appropriate exception.

        :param timeout: maximum amount of time to wait until the transaction is
            confirmed or fails
        :param poll_period: how much time to wait in between state checks
        :return: the transaction's result

        :raise ValueError: if ``timeout`` is negative
        :raise ValueError: if ``poll_period`` is not positive
        :raise TimeoutError: if ``timeout`` elapsed and the transaction has not
            been confirmed or failed yet
        """

    @classmethod
    def _validate_get(
        cls, timeout: _datetime.timedelta, poll_period: _datetime.timedelta
    ) -> None:
        """(private, do not use)"""

        assert isinstance(timeout, _datetime.timedelta)
        assert isinstance(poll_period, _datetime.timedelta)

        if timeout < _datetime.timedelta():
            raise ValueError("`timeout` must not be negative")

        if poll_period <= _datetime.timedelta():
            raise ValueError("`poll_period` must be positive")

    @classmethod
    def _real(
        cls,
        w3: _web3.Web3,
        tx_hash: bytes,
        on_success: _t.Callable[[_web3_types.TxReceipt], T],
        *,
        on_failure: _t.Optional[
            _t.Callable[[_web3_types.TxReceipt], None]
        ] = None,
    ) -> Transaction[T]:
        """(private, do not use)"""
        return _RealTransaction(w3, tx_hash, on_success, on_failure)

    @classmethod
    def _fake_successful(cls, result: T) -> Transaction[T]:
        """(private, do not use)"""
        return _FakeSuccessfulTransaction(result)

    @classmethod
    def _fake_failed(cls, error: BaseException) -> Transaction[T]:
        """(private, do not use)"""
        return _FakeFailedTransaction(error)


class _RealTransaction(Transaction[T]):
    """(private, do not use)"""

    __w3: _web3.Web3
    __hash: _web3_types.Hash32

    __on_success: _t.Tuple[_t.Callable[[_web3_types.TxReceipt], T]]
    __on_failure: _t.Tuple[_t.Callable[[_web3_types.TxReceipt], None]]

    def __init__(
        self,
        w3: _web3.Web3,
        tx_hash: bytes,
        on_success: _t.Callable[[_web3_types.TxReceipt], T],
        on_failure: _t.Optional[_t.Callable[[_web3_types.TxReceipt], None]],
    ) -> None:
        """(private, do not use)"""

        assert isinstance(tx_hash, bytes)
        assert len(tx_hash) == 32

        self.__w3 = w3
        self.__hash = _web3_types.Hash32(tx_hash)

        self.__on_success = (on_success,)
        self.__on_failure = (
            (lambda _: None) if on_failure is None else on_failure,
        )

    def is_done(self) -> bool:

        try:
            self.__w3.eth.getTransactionReceipt(self.__hash)
        except _web3_exceptions.TransactionNotFound:
            return False
        else:
            return True

    def get(
        self,
        *,
        timeout: _datetime.timedelta = _datetime.timedelta(minutes=2),
        poll_period: _datetime.timedelta = _datetime.timedelta(seconds=0.1),
    ) -> T:

        # validate arguments

        Transaction._validate_get(timeout=timeout, poll_period=poll_period)

        # fail immediately if timeout is zero and transaction is not done

        if timeout == _datetime.timedelta() and not self.is_done():
            raise TimeoutError("Transaction still pending confirmation")

        # await transaction confirmation

        try:
            receipt = self.__w3.eth.waitForTransactionReceipt(
                transaction_hash=self.__hash,
                timeout=_math.ceil(timeout.total_seconds()),
                poll_latency=poll_period.total_seconds(),
            )
        except _web3_exceptions.TimeExhausted:
            raise TimeoutError("Transaction still pending confirmation")

        # check transaction status

        if receipt["status"] != 1:
            self.__on_failure[0](receipt)
            raise ValueError("Transaction failed")

        # return result

        return self.__on_success[0](receipt)


class _FakeSuccessfulTransaction(Transaction[T]):
    """(private, do not use)"""

    __result: T

    def __init__(self, result: T) -> None:
        """(private, do not use)"""
        self.__result = result

    def is_done(self) -> bool:
        return True

    def get(
        self,
        *,
        timeout: _datetime.timedelta = _datetime.timedelta(minutes=2),
        poll_period: _datetime.timedelta = _datetime.timedelta(seconds=0.1),
    ) -> T:
        Transaction._validate_get(timeout=timeout, poll_period=poll_period)
        return self.__result


class _FakeFailedTransaction(Transaction[T]):
    """(private, do not use)"""

    __error: BaseException

    def __init__(self, error: BaseException) -> None:
        """(private, do not use)"""
        self.__error = error

    def is_done(self) -> bool:
        return True

    def get(
        self,
        *,
        timeout: _datetime.timedelta = _datetime.timedelta(minutes=2),
        poll_period: _datetime.timedelta = _datetime.timedelta(seconds=0.1),
    ) -> _t.NoReturn:
        Transaction._validate_get(timeout=timeout, poll_period=poll_period)
        raise self.__error


# ---------------------------------------------------------------------------- #


class LoanIdentifier:
    """
    Identifies a loan.

    Instances of this type are equality comparable and hashable.
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


class WrongLoanPhaseError(ValueError):
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
