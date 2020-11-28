// SPDX-License-Identifier: UNLICENSED
/* -------------------------------------------------------------------------- */

pragma solidity ^0.6.0;

import "./TuiChainToken.sol";

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/math/SafeMath.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";

/* -------------------------------------------------------------------------- */

contract TuiChainLoan is Ownable
{
    enum Phase { Funding, Expired, Canceled, Active, Finalized }

    /**
     * Emitted every time the phase is updated.
     *
     * @param newPhase The value to which the phase changed
     */
    event PhaseUpdated(Phase newPhase);

    /**
     * Emitted every time funds are provided.
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
     * Emitted every time funds are withdrawn.
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
     * Emitted every time tokens are claimed.
     *
     * @param claimer The address of the account or contract that claimed the
     *     tokens
     * @param amountTokens The number of tokens that were claimed
     */
    event TokensClaimed(address claimer, uint256 amountTokens);

    /**
     * Emitted every time a payment is made.
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
     * Emitted every time tokens are redeemed.
     *
     * @param redeemer The address of the account or contract that redeemed the
     *     tokens
     * @param amountTokens The number of tokens that were redeemed
     */
    event TokensRedeemed(address redeemer, uint256 amountTokens);

    /* ---------------------------------------------------------------------- */

    using SafeERC20 for IERC20;
    using SafeERC20 for TuiChainToken;
    using SafeMath for uint256;

    // The Dai contract.
    IERC20 private immutable dai;

    address private immutable feeRecipient;
    address private immutable loanRecipient;
    uint256 private immutable expirationTime;
    uint256 private immutable fundingFeeAttoDaiPerDai;
    uint256 private immutable paymentFeeAttoDaiPerDai;
    uint256 private immutable requestedValueDai;

    // The ERC-20 contract implementing the tokens for the loan. Only valid if
    // phase is Active or Finalized.
    TuiChainToken private immutable token;

    // The current phase of the loan.
    Phase private phase;

    // How much Dai has been funded. This may increase and decrease while phase
    // is Active, and equals requestedValueDai when phase is Active or
    // Finalized.
    uint256 private fundedDai;

    // How many tokens each address that funded the loan can still claim.
    mapping(address => uint256) private unclaimedTokens;

    // How much Dai has been paid by the student (or anyone, really) so far.
    uint256 private paidDai;

    // How much atto-Dai a token can be redeemed for. This is zero is every
    // phase but Finalized.
    uint256 private attoDaiPerToken;

    /* ---------------------------------------------------------------------- */

    /**
     * Note that the deployer is automatically assigned as the owner.
     *
     * @param _dai The Dai contract
     * @param _feeRecipient Address of EOA or contract to which fees are to be
     *     transferred
     * @param _loanRecipient Address of EOA or contract to which the loan value
     *     is to be transferred
     * @param _secondsToExpiration Maximum amount of time in seconds for the
     *     loan to be fully funded, after which it becomes expired
     * @param _fundingFeeAttoDaiPerDai Funding fee, in atto-Dai per Dai
     * @param _paymentFeeAttoDaiPerDai Payment fee, in atto-Dai per Dai
     * @param _requestedValueAttoDai Total requested loan value, in atto-Dai
     */
    constructor(
        IERC20 _dai,
        address _feeRecipient,
        address _loanRecipient,
        uint256 _secondsToExpiration,
        uint256 _fundingFeeAttoDaiPerDai,
        uint256 _paymentFeeAttoDaiPerDai,
        uint256 _requestedValueAttoDai
        ) public
    {
        require(_dai != IERC20(0));
        require(_feeRecipient != address(0));
        require(_loanRecipient != address(0));
        require(_secondsToExpiration > 0);

        uint256 _requestedValueDai = _attoDaiToPositiveWholeDai({
            _attoDai: _requestedValueAttoDai
            });

        dai = _dai;

        feeRecipient            = _feeRecipient;
        loanRecipient           = _loanRecipient;
        expirationTime          = block.timestamp.add(_secondsToExpiration);
        fundingFeeAttoDaiPerDai = _fundingFeeAttoDaiPerDai;
        paymentFeeAttoDaiPerDai = _paymentFeeAttoDaiPerDai;
        requestedValueDai       = _requestedValueDai;

        token = new TuiChainToken({
            _loan: this,
            _totalSupply: _requestedValueDai
            });

        phase           = Phase.Funding;
        fundedDai       = 0;
        paidDai         = 0;
        attoDaiPerToken = 0;
    }

    /* ---------------------------------------------------------------------- */

    /**
     * Ensure that the given value, which is expected to be in atto-Dai, is
     * positive and a multiple of 10^18, i.e., represents a positive and whole
     * amount of Dai, and return the given value converted to Dai.
     */
    function _attoDaiToPositiveWholeDai(uint256 _attoDai)
        private pure returns (uint256 _dai)
    {
        require(_attoDai > 0 && _attoDai.mod(1e18) == 0);

        return _attoDai.div(1e18);
    }

    function _updatePhase(Phase _newPhase) private
    {
        assert(phase != _newPhase);

        phase = _newPhase;

        emit PhaseUpdated({ newPhase: _newPhase });
    }

    function _tryExpire() private
    {
        if (phase == Phase.Funding && block.timestamp >= expirationTime)
            _updatePhase({ _newPhase: Phase.Expired });
    }

    /* ---------------------------------------------------------------------- */

    /**
     * Cancel the loan.
     *
     * Only the owner can invoke this function.
     *
     * This also checks if the loan has expired beforehand.
     *
     * Fails if current phase is not Funding or if the invocation causes the
     * contract to expire.
     */
    function cancel() external onlyOwner
    {
        _tryExpire();

        // checks

        require(phase == Phase.Funding);

        // effects

        _updatePhase({ _newPhase: Phase.Canceled });
    }

    /**
     * Finalize the loan.
     *
     * Phase must be Active and becomes Finalized.
     */
    function finalize() external onlyOwner
    {
        // checks

        require(phase == Phase.Active);

        // effects

        _updatePhase({ _newPhase: Phase.Finalized });

        attoDaiPerToken = paidDai.mul(1e18).div(requestedValueDai);
    }

    /* ---------------------------------------------------------------------- */

    /**
     * Return the ERC-20 contract implementing the loan's tokens.
     *
     * This is always valid, but note that this loan contract always holds the
     * entire token supply if Phase is Funding, Expired, or Canceled.
     */
    function getToken() public view returns (TuiChainToken _token)
    {
        return token;
    }

    /**
     * Expire the loan if the funding deadline has passed.
     *
     * Fails if current phase is not Funding or Expired.
     *
     * @return _expired true if the loan becomes or already was expired, false
     *     otherwise
     */
    function checkExpiration() public returns (bool _expired)
    {
        _tryExpire();

        require(phase == Phase.Funding || phase == Phase.Expired);

        return phase == Phase.Expired;
    }

    /**
     * Deposit some Dai to fund the loan.
     *
     * Fees are added to _valueAttoDai. The actual transferred value, in
     * atto-Dai, is given by:
     *
     *     _valueAttoDai + fundingFeeAttoDaiPerDai * (_valueAttoDai / 1e18)
     *
     * @param _valueAttoDai Amount of funds to provide (before fees) in atto-Dai
     */
    function provideFunds(uint256 _valueAttoDai) external
    {
        _tryExpire();

        // checks

        require(phase == Phase.Funding);

        uint256 valueDai = _attoDaiToPositiveWholeDai({
            _attoDai: _valueAttoDai
            });

        require(fundedDai.add(valueDai) <= requestedValueDai);

        // effects

        fundedDai = fundedDai.add(valueDai);
        unclaimedTokens[msg.sender] = unclaimedTokens[msg.sender].add(valueDai);

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
        }
    }

    /**
     * Withdraw some previously deposited Dai.
     *
     * Fees are added to _valueAttoDai. The actual transferred value, in
     * atto-Dai, is given by:
     *
     *     _valueAttoDai + fundingFeeAttoDaiPerDai * (_valueAttoDai / 1e18)
     *
     * @param _valueAttoDai Amount of funds to withdraw (before fees) in
     *     atto-Dai
     */
    function withdrawFunds(uint256 _valueAttoDai) external
    {
        _tryExpire();

        // checks

        require(
            phase == Phase.Funding || phase == Phase.Expired
            || phase == Phase.Canceled
            );

        uint256 valueDai = _attoDaiToPositiveWholeDai({
            _attoDai: _valueAttoDai
            });

        require(valueDai < unclaimedTokens[msg.sender]);

        // effects

        fundedDai = fundedDai.sub(valueDai);

        unclaimedTokens[msg.sender] = unclaimedTokens[msg.sender].sub(valueDai);

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
    }

    function claimTokens(uint256 _amountTokens) external
    {
        // checks

        require(phase == Phase.Active || phase == Phase.Finalized);
        require(_amountTokens > 0);
        require(_amountTokens <= unclaimedTokens[msg.sender]);

        // effects

        unclaimedTokens[msg.sender] =
            unclaimedTokens[msg.sender].sub(_amountTokens);

        emit TokensClaimed({
            claimer: msg.sender,
            amountTokens: _amountTokens
            });

        // interactions

        token.safeTransfer({ to: msg.sender, value: _amountTokens });
    }

    /**
     * TODO: document
     */
    function makePayment(uint256 _valueAttoDai) external
    {
        // checks

        require(phase == Phase.Active);

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
     * TODO: document
     */
    function redeemTokens(uint256 _amountTokens) external
    {
        // checks

        require(phase == Phase.Finalized);
        require(_amountTokens > 0);

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
