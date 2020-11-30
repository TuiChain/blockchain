# ---------------------------------------------------------------------------- #

# Synopsis:
#
#   Ethereum       - exposes all TuiChain Ethereum functionality
#   LoanState      - represents the state of a loan
#   LoanPhase      - enumeration of the possible phases of a loan
#   LoanPhaseError - error due to loan phase not being as expected

# ---------------------------------------------------------------------------- #

from __future__ import annotations

import datetime as _dt
import enum as _enum
import importlib.resources as _importlib_resources
import json as _json
import typing as _t

import eth_keys.datatypes as _eth_keys_datatypes
import web3 as _web3
import web3.providers as _web3_providers

# ---------------------------------------------------------------------------- #

with _importlib_resources.open_text(__package__, "abi.json") as f:
    _ABI: _t.Dict[str, _t.Any] = _json.load(f)

# ---------------------------------------------------------------------------- #


class LoanPhase(_enum.Enum):
    """Phases of a loan."""

    FUNDING = _enum.auto()
    """Loan has not yet been fully funded. Funders may deposited Dai."""

    EXPIRED = _enum.auto()
    """Loan funding did not reach requested value prior to the deadline. Funders
    may retrieve deposited Dai."""

    CANCELED = _enum.auto()
    """Loan was canceled prior to be fully funded. Funders may retrieve
    deposited Dai."""

    ACTIVE = _enum.auto()
    """Loan was fully funded and tokens were distributed to funders. Student is
    in debt, further payments may occur."""

    FINALIZED = _enum.auto()
    """Student is exempt from any further payments. Token owners may exchange
    them for Dai."""


# ---------------------------------------------------------------------------- #


class LoanState:
    """Information about the state of a loan."""

    @property
    def loan_contract_address(self) -> _web3.eth.Address:
        """Address of the loan's management contract."""

    @property
    def token_contract_address(self) -> _web3.eth.Address:
        """Address of the loan's ERC-20 token contract."""

    @property
    def fee_recipient_address(self) -> _web3.eth.Address:
        """Address of EOA or contract to which fees are to be transferred."""

    @property
    def loan_recipient_address(self) -> _web3.eth.Address:
        """Address of EOA or contract to which the loan value is to be
        transferred."""

    @property
    def creation_time(self) -> _dt.datetime:
        """Point in time at which the loan was created."""

    @property
    def funding_expiration_time(self) -> _dt.datetime:
        """Point in time at which the FUNDING phase is set to expire."""

    @property
    def funding_fee_atto_dai_per_dai(self) -> int:
        """Funding fee, in atto-Dai per Dai."""

    @property
    def payment_fee_atto_dai_per_dai(self) -> int:
        """Payment fee, in atto-Dai per Dai."""

    @property
    def requested_value_atto_dai(self) -> int:
        """Total requested loan value, in atto-Dai."""

    @property
    def phase(self) -> LoanPhase:
        """
        Current loan phase.

        This value can change across the lifetime of a loan.
        """

    @property
    def funded_value_atto_dai(self) -> int:
        """
        Loan value funded so far, in atto-Dai.

        Does not include payed funding fees. Equals requested_value_atto_dai if
        phase is ACTIVE or FINALIZED.

        This value can change across the lifetime of a loan.
        """

    @property
    def paid_value_atto_dai(self) -> int:
        """
        Total value paid so far, in atto-Dai.

        Does not include payed repayment fees. Equals 0 if phase is FUNDING,
        EXPIRED, or CANCELED.

        This value can change across the lifetime of a loan.
        """


# ---------------------------------------------------------------------------- #


class LoanPhaseError(ValueError):
    """An error caused by a loan not being in the expected phase."""

    __expected: LoanPhase
    __actual: LoanPhase

    def __init__(self, expected: LoanPhase, actual: LoanPhase) -> None:

        assert expected != actual

        super().__init__(
            f"expected loan phase {expected.name} but is {actual.name}"
        )

        self.__expected = expected
        self.__actual = actual

    @property
    def expected(self) -> LoanPhase:
        """The expected loan phase."""
        return self.__expected

    @property
    def actual(self) -> LoanPhase:
        """The actual loan phase."""
        return self.__actual


# ---------------------------------------------------------------------------- #


class Ethereum:
    """
    Exposes all TuiChain Ethereum functionality.

    This is the single interface provided by the blockchain team to the backend
    team. The constructor connects to an Ethereum client, and the instance's
    methods can then be used to create contracts and stuff.

    Current limitations:

    - Methods block until transactions are confirmed, which can take up to 3
      minutes. Interface must later be made asynchronous.

    - No attention has been paid to atomicity guarantees or exception safety so
      far.
    """

    def __init__(
        self,
        provider: _web3_providers.BaseProvider,
        account: _web3.Account,
        controller_contract_address: _web3.eth.Address,
        *,
        required_confirmations: int = 12,
        confirmation_timeout: _dt.timedelta = _dt.timedelta(minutes=5),
    ) -> None:
        """
        Connect to an Ethereum client.

        The private key is used for everything, from signing transactions to
        receiving funds.

        The provider specifies the client. Example providers:

        - web3.IPCProvider('./path/to/geth.ipc')
        - web3.HTTPProvider('http://127.0.0.1:8545')
        - web3.WebsocketProvider('ws://127.0.0.1:8546')

        required_confirmations is the number of blocks confirming the
        transaction that must be mined before the transaction is assumed to be
        irreversible. The default value of 12 is a recomendation by Vitalik
        Buterin, cf. https://ethereum.stackexchange.com/a/203
        """

    def get_market_fee(self) -> int:
        """ TODO: document """

    def set_market_fee(self, market_fee_atto_dai_per_nano_dai: int) -> None:
        """ TODO: document """

    def create_loan(
        self,
        *,
        loan_recipient_address: _web3.eth.Address,
        time_to_expiration: _dt.timedelta,
        funding_fee_atto_dai_per_dai: int,
        payment_fee_atto_dai_per_dai: int,
        requested_value_atto_dai: int,
    ) -> LoanState:
        """
        Create a new loan.

        This may use up some ether.

        Parameters are keyword-only to prevent mistakes.

        :param loan_recipient_address: (see homonymous field of LoanState)
        :param time_to_expiration: maximum amount of time for requested funding
            to be achieved (rounded up to seconds); field
            funding_expiration_time of LoanState is derived from the creation
            time and this parameter
        :param funding_fee_atto_dai_per_dai: (see homonymous field of LoanState)
        :param payment_fee_atto_dai_per_dai: (see homonymous field of LoanState)
        :param requested_value_atto_dai: (see homonymous field of LoanState)
        """

        # __account.address <-- address of master account

    def get_loan_state(
        self, loan_contract_address: _web3.eth.Address
    ) -> LoanState:
        """
        Return information about the state of a loan.

        This will fully trust the contract loan_contract_address, so MAKE
        SURE THAT IT WAS ACTUALLY CREATED BY create_loan().

        This never costs any ether.

        :raises ValueError: if no such loan exists
        """

    def try_expire_loan(self, loan_contract_address: _web3.eth.Address) -> bool:
        """
        Expire a loan that is currently in the CROWDSALE phase and whose funding
        deadline has passed without having been fully funded.

        - If the loan is in the CROWDSALE phase and its funding deadline has not
          yet passed, nothing is done and False is returned.
        - If the loan is in the CROWDSALE phase and its funding deadline has
          passed, the loan is transitioned to phase EXPIRED and True is
          returned.
        - If the loan is already in the EXPIRED phase, nothing is done and True
          is returned.

        This method is necessary since the loan management contract must be
        interacted with for it to notice that it expired, and get_loan_state()
        does not do so.

        This will fully trust the contract loan_contract_address, so MAKE
        SURE THAT IT WAS ACTUALLY CREATED BY create_loan().

        This may use up some ether.

        :raises ValueError: if no such loan exists
        :raise LoanPhaseError: if loan phase is not CROWDSALE or EXPIRED
        """

    def cancel_loan(self, loan_contract_address: _web3.eth.Address) -> None:
        """
        Cancel a loan that is currently in the FUNDING phase.

        This will fully trust the contract loan_contract_address, so MAKE
        SURE THAT IT WAS ACTUALLY CREATED BY create_loan().

        This may use up some ether.

        :raises ValueError: if no such loan exists
        :raise LoanPhaseError: if loan phase is not FUNDING
        """

    def finalize_loan(self, loan_contract_address: _web3.eth.Address) -> None:
        """
        Finalize a loan that is currently in the ACTIVE phase.

        This will fully trust the contract loan_contract_address, so MAKE
        SURE THAT IT WAS ACTUALLY CREATED BY create_loan().

        This may use up some ether.

        :raises ValueError: if no such loan exists
        :raise LoanPhaseError: if loan phase is not ACTIVE
        """


# ---------------------------------------------------------------------------- #
