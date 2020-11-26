// SPDX-License-Identifier: UNLICENSED
/* -------------------------------------------------------------------------- */

pragma solidity ^0.6.0;

import "./TuiChainLoan.sol";
import "./TuiChainMarket.sol";

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/math/SafeMath.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";

/* -------------------------------------------------------------------------- */

contract TuiChainController is Ownable
{
    // The Dai contract.
    IERC20 private immutable dai;

    TuiChainMarket private immutable market;

    mapping(TuiChainLoan => bool) private loans;

    /* ---------------------------------------------------------------------- */

    /**
     * The owner can later change the fee with setMarketFee().
     *
     * @param _dai The Dai contract
     * @param _marketFeeRecipient Address of EOA or contract to which market
     *     fees are to be transferred
     * @param _marketFeeAttoDaiPerNanoDai Market purchase fee, in atto-Dai per
     *     nano-Dai
     */
    constructor(
        IERC20 _dai,
        address _marketFeeRecipient,
        uint256 _marketFeeAttoDaiPerNanoDai
        ) public
    {
        require(_dai != IERC20(0));

        dai = _dai;

        market = new TuiChainMarket({
            _dai: _dai,
            _feeRecipient: _marketFeeRecipient,
            _feeAttoDaiPerNanoDai: _marketFeeAttoDaiPerNanoDai
            });
    }

    /* ---------------------------------------------------------------------- */

    /**
     * TODO: document
     */
    function setMarketFee(uint256 _marketFeeAttoDaiPerNanoDai)
        external onlyOwner
    {
        market.setFee({ _feeAttoDaiPerNanoDai: _marketFeeAttoDaiPerNanoDai });
    }

    /**
     * TODO: document
     */
    function createLoan(
        address _feeRecipient,
        address _loanRecipient,
        uint256 _secondsToExpiration,
        uint256 _fundingFeeAttoDaiPerDai,
        uint256 _paymentFeeAttoDaiPerDai,
        uint256 _requestedValueAttoDai
        ) external onlyOwner returns (TuiChainLoan _loan)
    {
        TuiChainLoan loan = new TuiChainLoan({
            _dai: dai,
            _feeRecipient: _feeRecipient,
            _loanRecipient: _loanRecipient,
            _secondsToExpiration: _secondsToExpiration,
            _fundingFeeAttoDaiPerDai: _fundingFeeAttoDaiPerDai,
            _paymentFeeAttoDaiPerDai: _paymentFeeAttoDaiPerDai,
            _requestedValueAttoDai: _requestedValueAttoDai
            });

        market.allowToken({ _token: loan.getToken() });

        loans[loan] = true;

        return loan;
    }

    /**
     * TODO: document
     */
    function cancelLoan(TuiChainLoan _loan) external onlyOwner
    {
        require(loans[_loan]);

        _loan.cancel();
    }

    /**
     * TODO: document
     */
    function finalizeLoan(TuiChainLoan _loan) external onlyOwner
    {
        require(loans[_loan]);

        _loan.finalize();
    }

    /* ---------------------------------------------------------------------- */

    /**
     * TODO: document
     */
    function getMarket() external view returns (TuiChainMarket _market)
    {
        return market;
    }
}

/* -------------------------------------------------------------------------- */
