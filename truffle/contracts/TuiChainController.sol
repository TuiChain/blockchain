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

/** Manages loan creation and a market instance. */
contract TuiChainController is Ownable
{
    /**
     * Emitted whenever a loan is created using createLoan().
     *
     * @param loan The created loan contract
     */
    event LoanCreated(TuiChainLoan loan);

    /* ---------------------------------------------------------------------- */

    /** The Dai contract. */
    IERC20 public immutable dai;

    /** The market contract. */
    TuiChainMarket public immutable market;

    /** Maps loan contracts created using createLoan() to true. */
    mapping(TuiChainLoan => bool) public loanIsValid;

    /** Array of all loans created using createLoan(), in order of creation. */
    TuiChainLoan[] public loans;

    /* ---------------------------------------------------------------------- */

    /**
     * Construct a TuiChainController.
     *
     * @param _dai The Dai contract
     * @param _marketFeeRecipient Address of account or contract to which market
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
        require(_dai != IERC20(0), "_dai is the zero address");

        dai = _dai;

        market = new TuiChainMarket({
            _dai: _dai,
            _feeRecipient: _marketFeeRecipient,
            _feeAttoDaiPerNanoDai: _marketFeeAttoDaiPerNanoDai
            });
    }

    /* ---------------------------------------------------------------------- */

    /**
     * Set the market purchase fee to the given value.
     *
     * Only the owner can invoke this function.
     *
     * @param _marketFeeAttoDaiPerNanoDai The new market purchase fee, in
     *     atto-Dai per nano-Dai
     */
    function setMarketFee(uint256 _marketFeeAttoDaiPerNanoDai)
        external onlyOwner
    {
        market.setFee({ _feeAttoDaiPerNanoDai: _marketFeeAttoDaiPerNanoDai });
    }

    /**
     * Create a loan.
     *
     * Only the owner can invoke this function.
     *
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
    function createLoan(
        address _feeRecipient,
        address _loanRecipient,
        uint256 _secondsToExpiration,
        uint256 _fundingFeeAttoDaiPerDai,
        uint256 _paymentFeeAttoDaiPerDai,
        uint256 _requestedValueAttoDai
        ) external onlyOwner returns (TuiChainLoan _loan)
    {
        // create loan contract

        TuiChainLoan loan = new TuiChainLoan({
            _dai: dai,
            _controller: this,
            _feeRecipient: _feeRecipient,
            _loanRecipient: _loanRecipient,
            _secondsToExpiration: _secondsToExpiration,
            _fundingFeeAttoDaiPerDai: _fundingFeeAttoDaiPerDai,
            _paymentFeeAttoDaiPerDai: _paymentFeeAttoDaiPerDai,
            _requestedValueAttoDai: _requestedValueAttoDai
            });

        // add loan contract to list of valid loans

        loanIsValid[loan] = true;
        loans.push(loan);

        // emit loan creation event

        emit LoanCreated({ loan: loan });

        // return loan contract

        return loan;
    }

    /**
     * Cancel the given loan.
     *
     * Fails if the loan is not in phase Funding.
     *
     * Only the owner can invoke this function.
     *
     * @param _loan The contract of the loan to be canceled
     */
    function cancelLoan(TuiChainLoan _loan) external onlyOwner
    {
        require(
            loanIsValid[_loan],
            "_loan is not a loan created by this controller"
            );

        _loan.cancel();
    }

    /**
     * Finalize the given loan.
     *
     * Fails if the loan is not in phase Active.
     *
     * Only the owner can invoke this function.
     *
     * @param _loan The contract of the loan to be finalized
     */
    function finalizeLoan(TuiChainLoan _loan) external onlyOwner
    {
        require(
            loanIsValid[_loan],
            "_loan is not a loan created by this controller"
            );

        _loan.finalize();

        market.removeToken({ _token: _loan.token() });
    }

    /* ---------------------------------------------------------------------- */

    /**
     * Return the number of loans created using createLoan().
     *
     * @return _numLoans The number of loans created using createLoan()
     */
    function numLoans() external view returns (uint256 _numLoans)
    {
        return loans.length;
    }

    /**
     * @dev Invoked by a loan contract to inform that it entered phase Active.
     */
    function notifyLoanActivation() external
    {
        TuiChainLoan loan = TuiChainLoan(msg.sender);

        require(
            loanIsValid[loan],
            "message sender is not a loan created by this controller"
            );

        market.addToken({ _token: loan.token() });
    }
}

/* -------------------------------------------------------------------------- */
