# ---------------------------------------------------------------------------- #

from __future__ import annotations

import datetime
import typing as t

import eth_tester
import eth_tester.backends.pyevm.main
import pytest
import web3
import web3.types

import util
import tuichain_ethereum._test as tui

# ---------------------------------------------------------------------------- #

# increase block gas limit
eth_tester.backends.pyevm.main.GENESIS_GAS_LIMIT = 8_000_000

# ---------------------------------------------------------------------------- #


@pytest.fixture
def chain() -> eth_tester.EthereumTester:
    """
    Create an :class:`eth_eth_tester.EthereumTester` test chain.

    :return: the test chain
    """

    ethereum_tester = eth_tester.EthereumTester()
    ethereum_tester.disable_auto_mine_transactions()

    return ethereum_tester


@pytest.fixture
def w3(chain: eth_tester.EthereumTester) -> web3.Web3:
    """
    Create a :class:`web3.Web3` instance for the
    :class:`eth_eth_tester.EthereumTester` test chain.

    :return: the :class:`web3.Web3` instance
    """

    w3 = web3.Web3(web3.EthereumTesterProvider(chain))
    w3.enable_strict_bytes_type_checking()

    return w3


@pytest.fixture
def accounts(
    chain: eth_tester.EthereumTester,
    w3: web3.Web3,
) -> t.Sequence[tui.PrivateKey]:
    """
    Create 10 accounts and credit each with 100 thousand ether.

    :return: the accounts' private keys
    """

    # generate private keys

    keys = tuple(tui.PrivateKey.random() for _ in range(10))

    assert len(keys) <= len(chain.get_accounts())

    # transfer ether to every account

    for (key, user) in zip(keys, chain.get_accounts()):

        chain.add_account(bytes(key).hex())

        w3.eth.sendTransaction(
            {
                "from": user,
                "to": key.address._checksummed,
                "value": web3.Web3.toWei(100_000, "ether"),
            }
        )

        chain.mine_block()

    # return private keys

    return keys


@pytest.fixture
def dai(
    chain: eth_tester.EthereumTester,
    accounts: t.Sequence[tui.PrivateKey],
    w3: web3.Web3,
) -> tui.DaiMockContract:
    """
    Deploy a mock Dai contract using account 0 and credit all accounts with 1
    million Dai.

    :return: the mock Dai contract
    """

    # deploy mock Dai contract

    transaction_deploy = tui.DaiMockContract.deploy(
        provider=w3.provider, account_private_key=accounts[0]
    )

    chain.mine_block()

    assert transaction_deploy.is_done()
    dai = transaction_deploy.get()

    # credit all accounts with 1 million Dai

    for acc in accounts:

        transaction_mint = dai.mint(
            account_address=acc.address, atto_dai=1_000_000 * (10 ** 18)
        )

        chain.mine_block()

        assert transaction_mint.is_done()
        transaction_mint.get()

    # return mock Dai contract

    return dai


@pytest.fixture
def controller(
    chain: eth_tester.EthereumTester,
    dai: tui.DaiMockContract,
    accounts: t.Sequence[tui.PrivateKey],
    w3: web3.Web3,
) -> tui.Controller:
    """
    Deploy a controller using account 0 and with a 1% market fee.

    :return: the deployed controller
    """

    transaction_deploy = tui.Controller.deploy(
        provider=w3.provider,
        master_account_private_key=accounts[0],
        dai_contract_address=dai.address,
        market_fee_atto_dai_per_nano_dai=10 ** 7,
    )

    chain.mine_block()

    assert transaction_deploy.is_done()

    return transaction_deploy.get()


def _finalized_loan(
    chain: eth_tester.EthereumTester,
    controller: tui.Controller,
    accounts: t.Sequence[tui.PrivateKey],
    w3: web3.Web3,
) -> tui.Loan:

    # create loan in phase ACTIVE

    loan = _active_loan(chain, controller, accounts, w3)

    # finalize loan

    transaction_finalize = loan.finalize()

    chain.mine_block()

    assert transaction_finalize.is_done()
    transaction_finalize.get()

    assert loan.get_state().phase == tui.LoanPhase.FINALIZED

    # return loan

    return loan


@pytest.fixture
def funding_loan(
    chain: eth_tester.EthereumTester,
    controller: tui.Controller,
    accounts: t.Sequence[tui.PrivateKey],
) -> tui.Loan:
    """
    Create a loan with:

    - account 1 as the recipient,
    - 1 minute to expiration,
    - a funding fee of 5%,
    - a payment fee of 10%, and
    - a requested value of 20 thousand Dai.

    :return: the loan, which is in phase FUNDING
    """

    return _funding_loan(chain, controller, accounts)


@pytest.fixture
def active_loan(
    chain: eth_tester.EthereumTester,
    controller: tui.Controller,
    accounts: t.Sequence[tui.PrivateKey],
    w3: web3.Web3,
) -> tui.Loan:
    """
    Create a loan with:

    - account 1 as the recipient,
    - 1 minute to expiration,
    - a funding fee of 5%,
    - a payment fee of 10%, and
    - a requested value of 20 thousand Dai,

    and then have account 2 provide the full requested value.

    :return: the loan, which is in phase ACTIVE
    """

    return _active_loan(chain, controller, accounts, w3)


def _active_loan(
    chain: eth_tester.EthereumTester,
    controller: tui.Controller,
    accounts: t.Sequence[tui.PrivateKey],
    w3: web3.Web3,
) -> tui.Loan:

    # create loan in phase FUNDING

    loan = _funding_loan(chain, controller, accounts)

    # fully fund loan

    util.execute_user_transactions(
        w3=w3,
        from_address=accounts[2].address,
        transactions=loan.user_transaction_builder.provide_funds(
            value_atto_dai=loan.requested_value_atto_dai
        ),
    )

    assert loan.get_state().phase == tui.LoanPhase.ACTIVE

    # return loan

    return loan


@pytest.fixture
def finalized_loan(
    chain: eth_tester.EthereumTester,
    controller: tui.Controller,
    accounts: t.Sequence[tui.PrivateKey],
    w3: web3.Web3,
) -> tui.Loan:
    """
    Create a loan with:

    - account 1 as the recipient,
    - 1 minute to expiration,
    - a funding fee of 5%,
    - a payment fee of 10%, and
    - a requested value of 20 thousand Dai,

    then have account 2 provide the full requested value, and then finalize the
    loan.

    :return: the loan, which is in phase FINALIZED
    """

    return _finalized_loan(chain, controller, accounts, w3)


def _funding_loan(
    chain: eth_tester.EthereumTester,
    controller: tui.Controller,
    accounts: t.Sequence[tui.PrivateKey],
) -> tui.Loan:

    transaction_create = controller.loans.create(
        recipient_address=accounts[1].address,
        time_to_expiration=datetime.timedelta(minutes=1),
        funding_fee_atto_dai_per_dai=5 * (10 ** 16),
        payment_fee_atto_dai_per_dai=10 * (10 ** 16),
        requested_value_atto_dai=20_000 * (10 ** 18),
    )

    assert not transaction_create.is_done()

    chain.mine_block()
    assert transaction_create.is_done()

    loan = transaction_create.get()

    return loan


# ---------------------------------------------------------------------------- #
