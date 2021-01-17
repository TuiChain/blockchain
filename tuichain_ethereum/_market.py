# ---------------------------------------------------------------------------- #

from __future__ import annotations

import dataclasses as _dataclasses
import functools as _functools
import typing as _t

import eth_utils as _eth_utils
import web3.contract as _web3_contract
import web3.exceptions as _web3_exceptions

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
    __contract: _web3_contract.Contract

    def __init__(self, controller: Controller) -> None:
        """(private, do not use)"""

        self.__controller = controller

        self.__contract = self.__controller._w3.eth.contract(
            address=_eth_utils.to_checksum_address(
                self.__controller._contract.caller.market()
            ),
            abi=_tuichain_contracts.TuiChainMarket.ABI,
        )

    @property
    def _controller(self) -> Controller:
        """(private, do not use)"""
        return self.__controller

    @property
    def _contract(self) -> _web3_contract.Contract:
        """(private, do not use)"""
        return self.__contract

    @_functools.cached_property
    def user_transaction_builder(self) -> MarketUserTransactionBuilder:
        """The user transaction builder for the market."""
        return MarketUserTransactionBuilder(market=self)

    def get_fee_atto_dai_per_nano_dai(self) -> int:
        """Return the current market purchase fee, in atto-Dai per nano-Dai."""
        return int(self.__contract.caller.feeAttoDaiPerNanoDai())

    def set_fee(self, *, fee_atto_dai_per_nano_dai: int) -> Transaction[None]:
        """
        Set the market purchase fee.

        Currency parameters are keyword-only to prevent mistakes.

        This action may use up some ether from the master account.

        :param fee_atto_dai_per_nano_dai: the new market purchase fee, in
            atto-Dai per nano-Dai

        :return: the corresponding transaction

        :raise ValueError: if ``fee_atto_dai_per_nano_dai`` is negative
        """

        # validate argument

        assert isinstance(fee_atto_dai_per_nano_dai, int)

        if fee_atto_dai_per_nano_dai < 0:
            raise ValueError("`fee_atto_dai_per_nano_dai` must not be negative")

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

        caller = self.__contract.caller(
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

            token_contract = self.__controller._token_contract_factory(
                address=token
            )

            loan = Loan(
                controller=self.__controller,
                identifier=LoanIdentifier(token_contract.caller.loan()),
            )

            yield SellPosition(
                loan=loan,
                seller_address=Address(seller),
                amount_tokens=int(amount_tokens),
                price_atto_dai_per_token=int(price_atto_dai_per_token),
            )

    def get_sell_positions_by_loan(
        self, loan: Loan
    ) -> _t.Iterable[SellPosition]:
        """
        Return an iterable over all existing sell positions offering tokens of
        the given loan, in no particular order.

        The iterable always provides a consistent snapshot of the set of
        existing sell positions, no matter how slowly it is iterated over.
        """

        assert isinstance(loan, Loan)

        return (
            position
            for position in self.get_all_sell_positions()
            if position.loan.identifier == loan.identifier
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

        assert isinstance(seller_address, Address)

        return (
            position
            for position in self.get_all_sell_positions()
            if position.seller_address == seller_address
        )

    def get_sell_position_by_loan_and_seller(
        self, loan: Loan, seller_address: Address
    ) -> _t.Optional[SellPosition]:
        """Return the sell position offering tokens of the given loan and whose
        seller has the given address, or ``None`` if no such sell position
        exists."""

        assert isinstance(loan, Loan)
        assert isinstance(seller_address, Address)

        try:

            [
                amount_tokens,
                price_atto_dai_per_token,
            ] = self.__contract.caller.getSellPosition(
                _token=loan.token_contract_address._checksummed,
                _seller=seller_address._checksummed,
            )

        except Exception as e:

            if "no such sell position" in str(e):
                return None
            else:
                raise

        else:

            return SellPosition(
                loan=loan,
                seller_address=seller_address,
                amount_tokens=int(amount_tokens),
                price_atto_dai_per_token=int(price_atto_dai_per_token),
            )

    def __eq__(self, other: _t.Any) -> bool:
        raise NotImplementedError

    def __hash__(self) -> int:
        raise NotImplementedError


# ---------------------------------------------------------------------------- #


class MarketUserTransactionBuilder:
    """Provides functionality to build transactions for users to interact with a
    loan contract."""

    __market: Market

    def __init__(self, market: Market) -> None:
        """(private, do not use)"""
        self.__market = market

    def create_sell_position(
        self,
        loan: Loan,
        amount_tokens: int,
        *,
        price_atto_dai_per_token: int,
    ) -> _t.Sequence[UserTransaction]:
        """
        Build a sequence of transactions for a user to create a sell position.

        Currency parameters are keyword-only to prevent mistakes.

        :param loan: the loan whose token the sell position refers to
        :param amount_tokens: the number of tokens to offer
        :param price_atto_dai_per_token: the price, in atto-Dai per token

        :return: the sequence of transactions to be submitted by the user

        :raise ValueError: if there already exists a sell position by the user
            offering tokens of the given loan
        :raise ValueError: if ``amount_tokens`` is not positive
        :raise ValueError: if ``price_atto_dai_per_token`` is not a positive
            multiple of 1 nano-Dai
        """

        # validate arguments

        assert isinstance(loan, Loan)
        assert isinstance(amount_tokens, int)
        assert isinstance(price_atto_dai_per_token, int)

        if amount_tokens <= 0:
            raise ValueError("`amount_tokens` must be positive")

        if (
            price_atto_dai_per_token <= 0
            or price_atto_dai_per_token % (10 ** 9) != 0
        ):
            raise ValueError(
                "`price_atto_dai_per_token` must be a positive multiple of 1"
                " nano-Dai"
            )

        # build and return transactions

        return UserTransaction._build_sequence(
            # set token allowance for User --> Market transfer
            loan._token_contract.functions.approve(
                spender=self.__market._contract.address,
                amount=amount_tokens,
            ),
            # create sell position
            self.__market._contract.functions.createSellPosition(
                _token=loan.token_contract_address._checksummed,
                _amountTokens=amount_tokens,
                _priceAttoDaiPerToken=price_atto_dai_per_token,
            ),
        )

    def remove_sell_position(self, loan: Loan) -> _t.Sequence[UserTransaction]:
        """
        Build a sequence of transactions for a user to remove an existing sell
        position.

        :param loan: the loan whose token the sell position refers to

        :return: the sequence of transactions to be submitted by the user

        :raise ValueError: if there exists no sell position by the user offering
            tokens of the given loan
        """

        # validate arguments

        assert isinstance(loan, Loan)

        # build and return transactions

        return UserTransaction._build_sequence(
            # remove sell position
            self.__market._contract.functions.removeSellPosition(
                _token=loan.token_contract_address._checksummed
            ),
        )

    def increase_sell_position_amount(
        self,
        loan: Loan,
        increase_amount: int,
    ) -> _t.Sequence[UserTransaction]:
        """
        Build a sequence of transactions for a user to increase the token amount
        of an existing sell position.

        :param loan: the loan whose token the sell position refers to
        :param increase_amount: the number of tokens to add to the amount
            offered by the sell position

        :return: the sequence of transactions to be submitted by the user

        :raise ValueError: if there exists no sell position by the user offering
            tokens of the given loan
        :raise ValueError: if ``increase_amount`` is not positive
        """

        # validate arguments

        assert isinstance(loan, Loan)
        assert isinstance(increase_amount, int)

        if increase_amount <= 0:
            raise ValueError("`increase_amount` must be positive")

        # build and return transactions

        return UserTransaction._build_sequence(
            # set token allowance for User --> Market transfer
            loan._token_contract.functions.approve(
                spender=self.__market._contract.address,
                amount=increase_amount,
            ),
            # increase sell position amount
            self.__market._contract.functions.increaseSellPositionAmount(
                _token=loan.token_contract_address._checksummed,
                _increaseAmount=increase_amount,
            ),
        )

    def decrease_sell_position_amount(
        self,
        loan: Loan,
        decrease_amount: int,
    ) -> _t.Sequence[UserTransaction]:
        """
        Build a sequence of transactions for a user to decrease the token amount
        of an existing sell position.

        :param loan: the loan whose token the sell position refers to
        :param decrease_amount: the number of tokens to subtract from the amount
            offered by the sell position

        :return: the sequence of transactions to be submitted by the user

        :raise ValueError: if there exists no sell position by the user offering
            tokens of the given loan
        :raise ValueError: if ``decrease_amount`` is not positive
        :raise ValueError: if ``decrease_amount`` exceeds the amount of tokens
            currently offered by the sell position
        """

        # validate arguments

        assert isinstance(loan, Loan)
        assert isinstance(decrease_amount, int)

        if decrease_amount <= 0:
            raise ValueError("`decrease_amount` must be positive")

        # build and return transactions

        return UserTransaction._build_sequence(
            # decrease sell position amount
            self.__market._contract.functions.decreaseSellPositionAmount(
                _token=loan.token_contract_address._checksummed,
                _decreaseAmount=decrease_amount,
            ),
        )

    def update_sell_position_price(
        self,
        loan: Loan,
        *,
        new_price_atto_dai_per_token: int,
    ) -> _t.Sequence[UserTransaction]:
        """
        Build a sequence of transactions for a user to update the price of an
        existing sell position.

        Currency parameters are keyword-only to prevent mistakes.

        :param loan: the loan whose token the sell position refers to
        :param new_price_atto_dai_per_token: the new price, in atto-Dai per
            token

        :return: the sequence of transactions to be submitted by the user

        :raise ValueError: if there exists no sell position by the user offering
            tokens of the given loan
        :raise ValueError: if ``price_atto_dai_per_token`` is not a positive
            multiple of 1 nano-Dai
        """

        # validate arguments

        assert isinstance(loan, Loan)
        assert isinstance(new_price_atto_dai_per_token, int)

        if (
            new_price_atto_dai_per_token <= 0
            or new_price_atto_dai_per_token % (10 ** 9) != 0
        ):
            raise ValueError(
                "`new_price_atto_dai_per_token` must be a positive multiple of"
                " 1 nano-Dai"
            )

        # build and return transactions

        return UserTransaction._build_sequence(
            # update sell position price
            self.__market._contract.functions.updateSellPositionPrice(
                _token=loan.token_contract_address._checksummed,
                _newPriceAttoDaiPerToken=new_price_atto_dai_per_token,
            ),
        )

    def purchase(
        self,
        loan: Loan,
        seller_address: Address,
        amount_tokens: int,
        *,
        price_atto_dai_per_token: int,
        fee_atto_dai_per_nano_dai: int,
    ) -> _t.Sequence[UserTransaction]:
        """
        Build a sequence of transactions for a user to purchase tokens from an
        existing sell position.

        Currency parameters are keyword-only to prevent mistakes.

        :param loan: the loan whose token the sell position refers to
        :param seller_address: the address of the seller
        :param amount_tokens: the number of tokens to offer
        :param price_atto_dai_per_token: the price, in atto-Dai per token
        :param fee_atto_dai_per_nano_dai: the market purchase fee, in atto-Dai
            per paid nano-Dai

        :return: the sequence of transactions to be submitted by the user

        :raise ValueError: if there is no such sell position
        :raise ValueError: if ``amount_tokens`` is not positive
        :raise ValueError: if ``price_atto_dai_per_token`` is not a positive
            multiple of 1 nano-Dai
        :raise ValueError: if ``fee_atto_dai_per_nano_dai`` is negative
        """

        # validate arguments

        assert isinstance(loan, Loan)
        assert isinstance(seller_address, Address)
        assert isinstance(amount_tokens, int)
        assert isinstance(price_atto_dai_per_token, int)
        assert isinstance(fee_atto_dai_per_nano_dai, int)

        if amount_tokens <= 0:
            raise ValueError("`amount_tokens` must be positive")

        if (
            price_atto_dai_per_token <= 0
            or price_atto_dai_per_token % (10 ** 9) != 0
        ):
            raise ValueError(
                "`price_atto_dai_per_token` must be a positive multiple of 1"
                " nano-Dai"
            )

        if fee_atto_dai_per_nano_dai < 0:
            raise ValueError("`fee_atto_dai_per_nano_dai` must not be negative")

        # build and return transactions

        total_price_atto_dai = price_atto_dai_per_token * amount_tokens
        fee = fee_atto_dai_per_nano_dai * (total_price_atto_dai // (10 ** 9))

        total_value = total_price_atto_dai + fee

        return UserTransaction._build_sequence(
            # set Dai allowance for User --> Loan transfer
            self.__market._controller._dai_contract.functions.approve(
                spender=self.__market._contract.address,
                amount=total_value,
            ),
            # make payment
            self.__market._contract.functions.purchase(
                _token=loan.token_contract_address._checksummed,
                _seller=seller_address._checksummed,
                _amountTokens=amount_tokens,
                _priceAttoDaiPerToken=price_atto_dai_per_token,
                _feeAttoDaiPerNanoDai=fee_atto_dai_per_nano_dai,
            ),
        )

    def __eq__(self, other: _t.Any) -> bool:
        raise NotImplementedError

    def __hash__(self) -> int:
        raise NotImplementedError


# ---------------------------------------------------------------------------- #
