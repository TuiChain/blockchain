// SPDX-License-Identifier: UNLICENSED
/* -------------------------------------------------------------------------- */

pragma solidity ^0.6.0;

import "./TuiChainController.sol";
import "./TuiChainToken.sol";

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/math/SafeMath.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";

/* -------------------------------------------------------------------------- */

/** Manages the entire life cycle of a loan. */
contract TuiChainLoan is Ownable
{
    using SafeERC20 for IERC20;
    using SafeERC20 for TuiChainToken;
    using SafeMath for uint256;

    /* ---------------------------------------------------------------------- */

    /**
     * Phases of a loan's life cycle.
     *
     * @param Funding Loan has not yet been fully funded, lenders may deposit
     *     Dai
     * @param Expired Loan funding did not reach requested value prior to the
     *     deadline, lenders may retrieve deposited Dai
     * @param Canceled Loan was canceled prior to be fully funded, lenders may
     *     retrieve deposited Dai
     * @param Active Loan was fully funded and tokens were distributed to
     *     lenders, student is in debt and further payments may occur
     * @param Finalized Student is exempt from any further payments, token
     *     owners may redeem them for Dai
     */
    enum Phase { Funding, Expired, Canceled, Active, Finalized }

    /**
     * Emitted whenever the loan's phase is updated.
     *
     * @param newPhase The new phase
     */
    event PhaseUpdated(Phase newPhase);

    /**
     * Emitted whenever funds are provided.
     *
     * @param funder The address of the account or contract that provided the
     *     funds
     * @param providedFundsAttoDai The amount of funds provided (excluding
     *     fees), in atto-Dai
     * @param newTotalFundedAttoDai The new total amount of available funds
     *     (excluding fees), in atto-Dai
     */
    event FundsProvided(
        address funder,
        uint256 providedFundsAttoDai,
        uint256 newTotalFundedAttoDai
        );

    /**
     * Emitted whenever funds are withdrawn.
     *
     * @param funder The address of the account or contract that withdrew the
     *     funds
     * @param withdrawnFundsAttoDai The amount of funds withdrawn (excluding
     *     fees), in atto-Dai
     * @param newTotalFundedAttoDai The new total amount of available funds
     *     (excluding fees), in atto-Dai
     */
    event FundsWithdrawn(
        address funder,
        uint256 withdrawnFundsAttoDai,
        uint256 newTotalFundedAttoDai
        );

    /**
     * Emitted whenever a payment is made.
     *
     * @param payer The address of the account or contract that made the payment
     * @param paymentAttoDai The payment's value (excluding fees), in atto-Dai
     * @param newTotalPaidAttoDai The new total paid value (excluding fees), in
     *     atto-Dai
     */
    event PaymentMade(
        address payer,
        uint256 paymentAttoDai,
        uint256 newTotalPaidAttoDai
        );

    /**
     * Emitted whenever tokens are redeemed.
     *
     * @param redeemer The address of the account or contract that redeemed the
     *     tokens
     * @param amountTokens The number of tokens that were redeemed
     */
    event TokensRedeemed(address redeemer, uint256 amountTokens);

    /* ---------------------------------------------------------------------- */

    /** The Dai contract. */
    IERC20 public immutable dai;

    /** The controller contract. */
    TuiChainController public immutable controller;

    /** Address of account or contract to which fees are to be transferred. */
    address public immutable feeRecipient;

    /**
     * Address of account or contract to which the loan value is to be
     * transferred.
     */
    address public immutable loanRecipient;

    /** Timestamp at which the loan was created. */
    uint256 public immutable creationTime;

    /** Timestamp at which the loan's Funding phase is set to expire. */
    uint256 public immutable expirationTime;

    /** Funding fee, in atto-Dai per Dai. */
    uint256 public immutable fundingFeeAttoDaiPerDai;

    /** Payment fee, in atto-Dai per Dai. */
    uint256 public immutable paymentFeeAttoDaiPerDai;

    /** Requested loan value, in atto-Dai. */
    uint256 public immutable requestedValueDai;

    /** The ERC-20 contract implementing the loan's token. */
    TuiChainToken public immutable token;

    /** The current phase of the loan. */
    Phase public phase;

    /**
     * How much Dai has been funded.
     *
     * This may increase and decrease while in phase Funding, and equals
     * requestedValueDai when in phase Active or Finalized.
     */
    uint256 public fundedDai;

    /** How much Dai has been paid by the student (or anyone, really) so far. */
    uint256 public paidDai;

    /**
     * How much atto-Dai a token can be redeemed for.
     *
     * This is zero is every phase but Finalized.
     */
    uint256 public attoDaiPerToken;

    /* ---------------------------------------------------------------------- */

    /**
     * Construct a TuiChainLoan.
     *
     * @param _dai The Dai contract
     * @param _feeRecipient Address of account or contract to which fees are to
     *     be transferred
     * @param _loanRecipient Address of account or contract to which the loan
     *     value is to be transferred
     * @param _secondsToExpiration Maximum amount of time in seconds for the
     *     loan to be fully funded, after which it becomes expired
     * @param _fundingFeeAttoDaiPerDai Funding fee, in atto-Dai per Dai
     * @param _paymentFeeAttoDaiPerDai Payment fee, in atto-Dai per Dai
     * @param _requestedValueAttoDai Requested loan value, in atto-Dai
     */
    constructor(
        IERC20 _dai,
        TuiChainController _controller,
        address _feeRecipient,
        address _loanRecipient,
        uint256 _secondsToExpiration,
        uint256 _fundingFeeAttoDaiPerDai,
        uint256 _paymentFeeAttoDaiPerDai,
        uint256 _requestedValueAttoDai
        ) public
    {
        require(_dai != IERC20(0), "_dai is the zero address");

        require(
            _controller != TuiChainController(0),
            "_controller is the zero address"
            );

        require(
            _feeRecipient != address(0),
            "_feeRecipient is the zero address"
            );

        require(
            _loanRecipient != address(0),
            "_loanRecipient is the zero address"
            );

        require(_secondsToExpiration > 0, "_secondsToExpiration is zero");

        uint256 _requestedValueDai = _attoDaiToPositiveWholeDai({
            _attoDai: _requestedValueAttoDai
            });

        dai = _dai;
        controller = _controller;

        feeRecipient = _feeRecipient;
        loanRecipient = _loanRecipient;
        creationTime = block.timestamp;
        expirationTime = block.timestamp.add(_secondsToExpiration);
        fundingFeeAttoDaiPerDai = _fundingFeeAttoDaiPerDai;
        paymentFeeAttoDaiPerDai = _paymentFeeAttoDaiPerDai;
        requestedValueDai = _requestedValueDai;

        token = new TuiChainToken({
            _loan: this,
            _totalSupply: _requestedValueDai
            });

        phase = Phase.Funding;
        fundedDai = 0;
        paidDai = 0;
        attoDaiPerToken = 0;
    }

    /* ---------------------------------------------------------------------- */

    /**
     * Ensure that the given value, which is expected to be in atto-Dai, is
     * positive and a multiple of 10^18, i.e., represents a positive multiple of
     * 1 Dai, and return the given value converted to Dai.
     *
     * @param _attoDai The input value, in atto-Dai
     * @return _dai The output value, in Dai
     */
    function _attoDaiToPositiveWholeDai(uint256 _attoDai)
        private pure returns (uint256 _dai)
    {
        require(
            _attoDai > 0 && _attoDai.mod(1e18) == 0,
            "not a positive multiple of 1 Dai"
            );

        return _attoDai.div(1e18);
    }

    /**
     * Set the phase to the given value.
     *
     * @param _newPhase The new phase
     */
    function _updatePhase(Phase _newPhase) private
    {
        assert(phase != _newPhase);

        phase = _newPhase;

        emit PhaseUpdated({ newPhase: _newPhase });
    }

    /** If applicable, expire the loan. */
    function _tryExpire() private
    {
        if (phase == Phase.Funding && block.timestamp >= expirationTime)
            _updatePhase({ _newPhase: Phase.Expired });
    }

    /* ---------------------------------------------------------------------- */

    /**
     * Cancel the loan.
     *
     * Fails if not in phase Funding.
     *
     * Only the owner can invoke this function.
     */
    function cancel() external onlyOwner
    {
        _tryExpire();

        // checks

        require(phase == Phase.Funding, "wrong phase");

        // effects

        _updatePhase({ _newPhase: Phase.Canceled });
    }

    /**
     * Finalize the loan.
     *
     * Fails if not in phase Active.
     *
     * Only the owner can invoke this function.
     */
    function finalize() external onlyOwner
    {
        // checks

        require(phase == Phase.Active, "wrong phase");

        // effects

        _updatePhase({ _newPhase: Phase.Finalized });

        attoDaiPerToken = paidDai.mul(1e18).div(requestedValueDai);
    }

    /* ---------------------------------------------------------------------- */

    /**
     * Expire the loan if the funding deadline has passed.
     *
     * Fails if not in phase Funding or Expired.
     *
     * @return _expired true if the loan becomes or already was expired, false
     *     otherwise
     */
    function checkExpiration() external returns (bool _expired)
    {
        _tryExpire();

        require(
            phase == Phase.Funding || phase == Phase.Expired,
            "wrong phase"
            );

        return phase == Phase.Expired;
    }

    /**
     * Deposit some Dai to fund the loan, receiving the corresponding amount of
     * tokens in return.
     *
     * Fees are added to _valueAttoDai. The actual transferred value, in
     * atto-Dai, is given by:
     *
     *     _valueAttoDai + fundingFeeAttoDaiPerDai * (_valueAttoDai / 1e18)
     *
     * Fails if not in phase Funding.
     *
     * @param _valueAttoDai Amount of funds to provide (excluding fees) in
     *     atto-Dai
     */
    function provideFunds(uint256 _valueAttoDai) external
    {
        _tryExpire();

        // checks

        require(phase == Phase.Funding, "wrong phase");

        uint256 valueDai = _attoDaiToPositiveWholeDai({
            _attoDai: _valueAttoDai
            });

        require(
            fundedDai.add(valueDai) <= requestedValueDai,
            "_valueAttoDai exceeds remaining requested funding"
            );

        // effects

        fundedDai = fundedDai.add(valueDai);

        emit FundsProvided({
            funder: msg.sender,
            providedFundsAttoDai: _valueAttoDai,
            newTotalFundedAttoDai: fundedDai.mul(1e18)
            });

        if (fundedDai == requestedValueDai)
            _updatePhase({ _newPhase: Phase.Active });

        // interactions

        uint256 feeAttoDai = fundingFeeAttoDaiPerDai.mul(valueDai);

        dai.safeTransferFrom({
            from: msg.sender,
            to: address(this),
            value: _valueAttoDai.add(feeAttoDai)
            });

        token.safeTransfer({ to: msg.sender, value: valueDai });

        if (fundedDai == requestedValueDai)
        {
            dai.safeTransfer({
                to: loanRecipient,
                value: requestedValueDai.mul(1e18)
                });

            dai.safeTransfer({
                to: feeRecipient,
                value: fundingFeeAttoDaiPerDai.mul(requestedValueDai)
                });

            controller.notifyLoanActivation();
        }
    }

    /**
     * Withdraw some previously deposited Dai, giving back the corresponding
     * amount of tokens.
     *
     * Fees are added to _valueAttoDai. The actual transferred value, in
     * atto-Dai, is given by:
     *
     *     _valueAttoDai + fundingFeeAttoDaiPerDai * (_valueAttoDai / 1e18)
     *
     * Fails if not in phase Funding, Expired, or Canceled.
     *
     * @param _valueAttoDai Amount of funds to withdraw (excluding fees) in
     *     atto-Dai
     */
    function withdrawFunds(uint256 _valueAttoDai) external
    {
        _tryExpire();

        // checks

        require(
            phase == Phase.Funding || phase == Phase.Expired
                || phase == Phase.Canceled,
            "wrong phase"
            );

        uint256 valueDai = _attoDaiToPositiveWholeDai({
            _attoDai: _valueAttoDai
            });

        // effects

        fundedDai = fundedDai.sub(valueDai);

        emit FundsWithdrawn({
            funder: msg.sender,
            withdrawnFundsAttoDai: _valueAttoDai,
            newTotalFundedAttoDai: fundedDai.mul(1e18)
            });

        // interactions

        uint256 feeAttoDai = fundingFeeAttoDaiPerDai.mul(valueDai);

        dai.safeTransfer({
            to: msg.sender,
            value: _valueAttoDai.add(feeAttoDai)
            });

        token.safeTransferFrom({
            from: msg.sender,
            to: address(this),
            value: valueDai
            });
    }

    /**
     * Make a payment.
     *
     * Fees are added to _valueAttoDai. The actual transferred value, in
     * atto-Dai, is given by:
     *
     *     _valueAttoDai + paymentFeeAttoDaiPerDai * (_valueAttoDai / 1e18)
     *
     * Fails if not in phase Active.
     *
     * @param _valueAttoDai Payment value (excluding fees) in atto-Dai
     */
    function makePayment(uint256 _valueAttoDai) external
    {
        // checks

        require(phase == Phase.Active, "wrong phase");

        uint256 valueDai = _attoDaiToPositiveWholeDai({
            _attoDai: _valueAttoDai
            });

        // effects

        paidDai = paidDai.add(valueDai);

        emit PaymentMade({
            payer: msg.sender,
            paymentAttoDai: _valueAttoDai,
            newTotalPaidAttoDai: paidDai.mul(1e18)
            });

        // interactions

        uint256 feeAttoDai = paymentFeeAttoDaiPerDai.mul(valueDai);

        dai.safeTransferFrom({
            from: msg.sender,
            to: address(this),
            value: _valueAttoDai.add(feeAttoDai)
            });

        dai.safeTransfer({ to: feeRecipient, value: feeAttoDai });
    }

    /**
     * Redeem some tokens, receiving the corresponding amount of Dai in return.
     *
     * Fails if not in phase Finalized.
     *
     * @param _amountTokens Number of tokens to redeem
     */
    function redeemTokens(uint256 _amountTokens) external
    {
        // checks

        require(phase == Phase.Finalized, "wrong phase");
        require(_amountTokens > 0, "_amountTokens is zero");

        // effects

        emit TokensRedeemed({
            redeemer: msg.sender,
            amountTokens: _amountTokens
            });

        // interactions

        token.burnFrom({ account: msg.sender, amount: _amountTokens });

        dai.safeTransfer({
            to: msg.sender,
            value: attoDaiPerToken.mul(_amountTokens)
            });
    }
}

/* -------------------------------------------------------------------------- */
