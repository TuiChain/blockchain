// SPDX-License-Identifier: UNLICENSED
/* -------------------------------------------------------------------------- */

pragma solidity ^0.6.0;

import "./TuiChainLoanToken.sol";

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/math/SafeMath.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";

contract TuiChainLoanManagement is Ownable
{
    using SafeERC20 for IERC20;
    using SafeERC20 for TuiChainLoanToken;
    using SafeMath for uint256;

    enum Phase { Funding, Expired, Canceled, Active, Finalized }

    /**
     * Emitted every time the phase is updated.
     *
     * @param newPhase the value to which the phase changed
     */
    event PhaseUpdate(Phase newPhase);

    /**
     * Emitted every time funds are provided or withdrawn.
     *
     * @param oldFundedDaiWei the previous amount of available funds (before
     *     fees), in Dai Wei
     * @param oldFundedDaiWei the new amount of available funds (before fees),
     *     in Dai Wei
     */
    event FundsUpdate(uint256 oldFundedDaiWei, uint256 newFundedDaiWei);

    /**
     * Emitted every time a payment is made.
     *
     * @param oldPaidDaiWei the previous total value paid (before fees), in Dai
     *     Wei
     * @param newPaidDaiWei the new total value paid (before fees), in Dai Wei
     */
    event Payment(uint256 oldPaidDaiWei, uint256 newPaidDaiWei);

    // The Dai contract.
    IERC20 private constant dai =
        IERC20(0x6B175474E89094C44Da98b954EedeAC495271d0F);

    address private immutable feeRecipient;
    address private immutable loanRecipient;
    uint256 private immutable expirationTime;
    uint256 private immutable fundingFeeDaiWeiPerDai;
    uint256 private immutable paymentFeeDaiWeiPerDai;
    uint256 private immutable requestedValueDai;

    // The current phase of the loan.
    Phase private phase;

    // The ERC-20 contract implementing the tokens for the loan. Only valid if
    // phase is Active or Finalized.
    TuiChainLoanToken private loanToken;

    // How much Dai has been funded. This may increase and decrease while phase
    // is Active, and equals requestedValueDai when phase is Active or
    // Finalized.
    uint256 private fundedDai;

    // How many tokens each address that funded the loan can still claim.
    mapping(address => uint256) private unclaimedTokens;

    // How much Dai has been paid by the student (or anyone, really) so far.
    uint256 private paidDai;

    // How much Dai Wei a token can be redeemed for. This is zero is every phase
    // but Finalized.
    uint256 private daiWeiPerToken;

    /**
     * Note that the deployer is automatically assigned as the owner.
     *
     * @param _feeRecipient Address of EOA or contract to which fees are to be
     *     transferred
     * @param _loanRecipient Address of EOA or contract to which the loan value
     *     is to be transferred
     * @param _secondsToExpiration Maximum amount of time in seconds for the
     *     loan to be fully funded, after which it becomes expired
     * @param _fundingFeeDaiWeiPerDai Funding fee, in Dai Wei per Dai
     * @param _paymentFeeDaiWeiPerDai Payment fee, in Dai Wei per Dai
     * @param _requestedValueDaiWei Total requested loan value, in Dai Wei
     */
    constructor(
        address _feeRecipient,
        address _loanRecipient,
        uint256 _secondsToExpiration,
        uint256 _fundingFeeDaiWeiPerDai,
        uint256 _paymentFeeDaiWeiPerDai,
        uint256 _requestedValueDaiWei
        ) public
    {
        require(_feeRecipient != address(0));
        require(_loanRecipient != address(0));
        require(_secondsToExpiration > 0);

        uint256 _requestedValueDai = _requirePositiveIntegerDai(
            _requestedValueDaiWei);

        feeRecipient           = _feeRecipient;
        loanRecipient          = _loanRecipient;
        expirationTime         = block.timestamp.add(_secondsToExpiration);
        fundingFeeDaiWeiPerDai = _fundingFeeDaiWeiPerDai;
        paymentFeeDaiWeiPerDai = _paymentFeeDaiWeiPerDai;
        requestedValueDai      = _requestedValueDai;

        phase          = Phase.Funding;
        loanToken      = TuiChainLoanToken(0);
        fundedDai      = 0;
        paidDai        = 0;
        daiWeiPerToken = 0;
    }

    function _requirePositiveIntegerDai(
        uint256 _daiWei) private pure returns (uint256 _dai)
    {
        require(
            _daiWei > 0 && _daiWei.mod(1e18) == 0,
            "Must be a positive, integer amount of Dai (multiple of 10^18)");

        return _daiWei.div(1e18);
    }

    function _updatePhase(Phase _newPhase) private
    {
        assert(phase != _newPhase);

        phase = _newPhase;
        emit PhaseUpdate(_newPhase);
    }

    function _tryExpire() private
    {
        if (phase == Phase.Funding && block.timestamp >= expirationTime)
            _updatePhase(Phase.Expired);
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
     * Fees are added to _valueDaiWei. The actual transferred value, in Dai Wei,
     * is given by:
     *
     *     _valueDaiWei + fundingFeeDaiWeiPerDai * (_valueDaiWei / 1e18)
     *
     * @param _valueDaiWei Amount of funds to provide (before fees) in Dai Wei
     */
    function provideFunds(uint256 _valueDaiWei) external
    {
        _tryExpire();

        // checks

        require(phase == Phase.Funding);

        uint256 valueDai = _requirePositiveIntegerDai(_valueDaiWei);
        require(fundedDai.add(valueDai) <= requestedValueDai);

        // effects

        emit FundsUpdate(
            fundedDai.mul(1e18), fundedDai.add(valueDai).mul(1e18));

        fundedDai = fundedDai.add(valueDai);
        unclaimedTokens[msg.sender] = unclaimedTokens[msg.sender].add(valueDai);

        if (fundedDai == requestedValueDai)
        {
            _updatePhase(Phase.Active);

            loanToken = new TuiChainLoanToken(requestedValueDai);
        }

        // interactions

        uint256 feeDaiWei = fundingFeeDaiWeiPerDai.mul(valueDai);

        dai.safeTransferFrom(
            msg.sender, address(this), _valueDaiWei.add(feeDaiWei));

        if (fundedDai == requestedValueDai)
        {
            dai.safeTransfer(loanRecipient, requestedValueDai.mul(1e18));

            dai.safeTransfer(
                feeRecipient, fundingFeeDaiWeiPerDai.mul(requestedValueDai));
        }
    }

    /**
     * Withdraw some previously deposited Dai.
     *
     * Fees are added to _valueDaiWei. The actual transferred value, in Dai Wei,
     * is given by:
     *
     *     _valueDaiWei + fundingFeeDaiWeiPerDai * (_valueDaiWei / 1e18)
     *
     * @param _valueDaiWei Amount of funds to withdraw (before fees) in Dai Wei
     */
    function withdrawFunds(uint256 _valueDaiWei) external
    {
        _tryExpire();

        // checks

        require(
            phase == Phase.Funding || phase == Phase.Expired
            || phase == Phase.Canceled);

        uint256 valueDai = _requirePositiveIntegerDai(_valueDaiWei);
        require(valueDai < unclaimedTokens[msg.sender]);

        // effects

        emit FundsUpdate(
            fundedDai.mul(1e18), fundedDai.sub(valueDai).mul(1e18));

        fundedDai = fundedDai.sub(valueDai);
        unclaimedTokens[msg.sender] = unclaimedTokens[msg.sender].sub(valueDai);

        // interactions

        uint256 feeDaiWei = fundingFeeDaiWeiPerDai.mul(valueDai);
        dai.safeTransfer(msg.sender, _valueDaiWei.add(feeDaiWei));
    }

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

        _updatePhase(Phase.Canceled);
    }

    /**
     * Return the ERC-20 contract implementing the loan's tokens.
     *
     * This also checks if the loan has expired beforehand.
     *
     * Fails if current phase is not Active or Finalized.
     */
    function token() public view returns (TuiChainLoanToken _token)
    {
        require(phase == Phase.Active || phase == Phase.Finalized);

        return loanToken;
    }

    function claimTokens(uint256 _tokens) external
    {
        // checks

        require(phase == Phase.Active || phase == Phase.Finalized);
        require(_tokens > 0);
        require(_tokens <= unclaimedTokens[msg.sender]);

        // effects

        unclaimedTokens[msg.sender] = unclaimedTokens[msg.sender].sub(_tokens);

        // interactions

        loanToken.safeTransfer(msg.sender, _tokens);
    }

    /**
     * TODO: document
     */
    function makePayment(uint256 _valueDaiWei) external
    {
        // checks

        require(phase == Phase.Active);
        uint256 valueDai = _requirePositiveIntegerDai(_valueDaiWei);

        // effects

        emit Payment(paidDai.mul(1e18), paidDai.add(valueDai).mul(1e18));

        paidDai = paidDai.add(valueDai);

        // interactions

        uint256 feeDaiWei = paymentFeeDaiWeiPerDai.mul(valueDai);

        dai.safeTransferFrom(
            msg.sender, address(this), _valueDaiWei.add(feeDaiWei));

        dai.safeTransfer(feeRecipient, feeDaiWei);
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

        _updatePhase(Phase.Finalized);

        daiWeiPerToken = paidDai.mul(1e18).div(requestedValueDai);
    }

    /**
     * TODO: document
     */
    function redeemTokens(uint256 _tokens) external
    {
        // checks

        require(phase == Phase.Finalized);
        require(_tokens > 0);

        // interactions

        loanToken.burnFrom(msg.sender, _tokens);
        dai.safeTransfer(msg.sender, daiWeiPerToken.mul(_tokens));
    }
}

/* -------------------------------------------------------------------------- */
