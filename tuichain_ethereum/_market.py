# ---------------------------------------------------------------------------- #

from __future__ import annotations

import dataclasses as _dataclasses
import functools as _functools
import typing as _t

import eth_utils as _eth_utils
import web3.contract as _web3_contract

import tuichain_ethereum._contracts as _tuichain_contracts

from tuichain_ethereum._loans import *

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


class Market:
    """A handle to a market contract."""

    __controller: Controller

    def __init__(self, controller: Controller) -> None:
        """(private, do not use)"""
        self.__controller = controller

    @property
    def _controller(self) -> Controller:
        """(private, do not use)"""
        return self.__controller

    @_functools.cached_property
    def _contract(self) -> _web3_contract.Contract:
        """(private, do not use)"""
        return self.__controller._w3.eth.contract(
            address=_eth_utils.to_checksum_address(
                self.__controller._contract.caller.market()
            ),
            abi=_tuichain_contracts.TuiChainMarket.ABI,
        )

    def get_fee_atto_dai_per_nano_dai(self) -> int:
        """Return the current market purchase fee, in atto-Dai per nano-Dai."""
        return int(self._contract.caller.feeAttoDaiPerNanoDai())

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

        tx_hash = self.__controller._master_account._transact(
            self.__controller._w3,
            self.__controller._contract.functions.setMarketFee(
                _marketFeeAttoDaiPerNanoDai=fee_atto_dai_per_nano_dai
            ),
        )

        # return transaction handle

        return Transaction._real(
            w3=self.__controller._w3, tx_hash=tx_hash, on_success=lambda _: None
        )

    def get_all_sell_positions(self) -> _t.Iterable[SellPosition]:
        """
        Return an iterable over all existing sell positions, in no particular
        order.

        The iterable always provides a consistent snapshot of the set of
        existing sell positions, no matter how slowly it is iterated over.
        """

        # get caller referencing specific block to ensure consistent snapshot

        caller = self._contract.caller(
            block_identifier=self.__controller._w3.eth.blockNumber
        )

        # yield every sell position

        for i in range(int(caller.numSellPositions())):

            [
                token,
                seller,
                amount_tokens,
                price_atto_dai_per_token,
            ] = caller.sellPositionAt(i)

            token_contract = self.__controller._w3.eth.contract(
                address=token,
                abi=_tuichain_contracts.TuiChainToken.ABI,
            )

            loan = Loan(
                controller=self.__controller,
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

        actual_loan: Loan

        if isinstance(loan, Loan):
            actual_loan = loan
        elif loan_obj := self.__controller.loans.get_by_identifier(loan):
            actual_loan = loan_obj
        else:
            return None

        [
            amount_tokens,
            price_atto_dai_per_token,
        ] = self._contract.caller.getSellPosition(
            _token=actual_loan.token_contract_address,
            _seller=seller_address._checksummed,
        )

        return SellPosition(
            loan=actual_loan,
            seller_address=seller_address,
            amount_tokens=int(amount_tokens),
            price_atto_dai_per_token=int(price_atto_dai_per_token),
        )


# ---------------------------------------------------------------------------- #
