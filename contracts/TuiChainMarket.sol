// SPDX-License-Identifier: UNLICENSED
/* -------------------------------------------------------------------------- */

pragma solidity ^0.6.0;

import "./TuiChainToken.sol";

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/math/SafeMath.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";

/* -------------------------------------------------------------------------- */

contract TuiChainMarket is Ownable
{
    /**
     * Emitted every time a purchase is made.
     *
     * @param token The ERC-20 contract implementing the token that was
     *     transacted
     * @param seller The address of the seller
     * @param buyer The address of the buyer
     * @param amountTokens The number of tokens that were transacted
     * @param priceAttoDaiPerToken The value paid by the buyer to the seller for
     *     each token (excluding fees), in atto-Dai
     * @param feeAttoDai The total fee paid by the buyer, in atto-Dai
     */
    event Transaction(
        TuiChainToken token,
        address seller,
        address buyer,
        uint256 amountTokens,
        uint256 priceAttoDaiPerToken,
        uint256 feeAttoDai
        );

    /* ---------------------------------------------------------------------- */

    struct SellPosition
    {
        uint256 amountTokens;
        uint256 priceNanoDaiPerToken;
    }

    using SafeERC20 for IERC20;
    using SafeERC20 for TuiChainToken;
    using SafeMath for uint256;

    // The Dai contract.
    IERC20 private immutable dai;

    // Address to which to send all collected fees.
    address private immutable feeRecipient;

    // Purchase fee, in atto-Dai per nano-Dai.
    uint256 private feeAttoDaiPerNanoDai;

    // True for an address if and only if it is the ERC-20 contract of a token
    // allowed to be exchanged in the market.
    mapping(TuiChainToken => bool) private allowedTokens;

    // token address => seller address => sell position
    mapping(TuiChainToken => mapping(address => SellPosition))
        private sellPositions;

    /* ---------------------------------------------------------------------- */

    /**
     * The owner can later change the fee with setFee().
     *
     * @param _dai The Dai contract
     * @param _feeRecipient Address of EOA or contract to which fees are to be
     *     transferred
     * @param _feeAttoDaiPerNanoDai Purchase fee, in atto-Dai per nano-Dai
     */
    constructor(
        IERC20 _dai,
        address _feeRecipient,
        uint256 _feeAttoDaiPerNanoDai
        ) public
    {
        require(_dai != IERC20(0));
        require(_feeRecipient != address(0));

        dai = _dai;

        feeRecipient         = _feeRecipient;
        feeAttoDaiPerNanoDai = _feeAttoDaiPerNanoDai;
    }

    /* ---------------------------------------------------------------------- */

    /**
     * Ensure that the given value, which is expected to be in atto-Dai, is
     * positive and a multiple of 10^9, i.e., represents a positive and whole
     * amount of nano-Dai, and return the given value converted to nano-Dai.
     */
    function _attoDaiToPositiveWholeNanoDai(uint256 _attoDai)
        private pure returns (uint256 _nanoDai)
    {
        require(_attoDai > 0 && _attoDai.mod(1e9) == 0);

        return _attoDai.div(1e9);
    }

    /* ---------------------------------------------------------------------- */

    // Add the given token to the set of allowed tokens.
    function allowToken(TuiChainToken _token) external onlyOwner
    {
        require(_token != TuiChainToken(0));

        allowedTokens[_token] = true;
    }

    // Set the fee to the given value.
    function setFee(uint256 _feeAttoDaiPerNanoDai) external onlyOwner
    {
        feeAttoDaiPerNanoDai = _feeAttoDaiPerNanoDai;
    }

    /* ---------------------------------------------------------------------- */

    /**
     * Return the current fee, in atto-Dai per payed nano-Dai.
     */
    function getFee() external view returns (uint256 _feeAttoDaiPerNanoDai)
    {
        return feeAttoDaiPerNanoDai;
    }

    /**
     * Add a new sell position.
     *
     * A sell position by the sender for the given token must not already exist.
     */
    function addSellPosition(
        TuiChainToken _token,
        uint256 _amountTokens,
        uint256 _priceAttoDaiPerToken
        ) external
    {
        // checks

        require(allowedTokens[_token]);

        SellPosition storage position = sellPositions[_token][msg.sender];

        require(position.amountTokens == 0, "sell position already exists");

        require(_amountTokens > 0);

        uint256 priceNanoDaiPerToken = _attoDaiToPositiveWholeNanoDai({
            _attoDai: _priceAttoDaiPerToken
            });

        // effects

        position.amountTokens         = _amountTokens;
        position.priceNanoDaiPerToken = priceNanoDaiPerToken;

        // interactions

        _token.safeTransferFrom({
            from: msg.sender,
            to: address(this),
            value: _amountTokens
            });
    }

    /**
     * Remove an existing sell position.
     */
    function removeSellPosition(TuiChainToken _token) external
    {
        // checks

        require(allowedTokens[_token]);

        uint256 amountTokens = sellPositions[_token][msg.sender].amountTokens;

        require(amountTokens > 0, "sell position does not exist");

        // effects

        delete sellPositions[_token][msg.sender];

        // interactions

        _token.safeTransfer({ to: msg.sender, value: amountTokens });
    }

    /**
     * Increase the token amount of an existing sell position.
     *
     * Functions are provided to increase and decrease the sell position amount
     * instead of having a single function to set it to a given value in order
     * to avoid attacks analogous to ERC-20's multiple withdrawal attack:
     *
     *     https://docs.google.com/document/d/1YLPtQxZu1UAvO9cZ1O2RPXBbT0mooh4DYKjA_jp-RLM
     */
    function increaseSellPositionAmount(
        TuiChainToken _token,
        uint256 _increaseAmount
        ) external
    {
        // checks

        require(allowedTokens[_token]);
        require(_increaseAmount > 0);

        SellPosition storage position = sellPositions[_token][msg.sender];

        require(position.amountTokens > 0, "sell position does not exist");

        // effects

        position.amountTokens = position.amountTokens.add(_increaseAmount);

        // interactions

        _token.safeTransferFrom({
            from: msg.sender,
            to: address(this),
            value: _increaseAmount
            });
    }

    /**
     * Decrease the token amount of an existing sell position.
     *
     * If _decreaseAmount is the same as the sell position's amount, the sell
     * position is removed.
     *
     * Functions are provided to increase and decrease the sell position amount
     * instead of having a single function to set it to a given value in order
     * to avoid attacks analogous to ERC-20's multiple withdrawal attack:
     *
     *     https://docs.google.com/document/d/1YLPtQxZu1UAvO9cZ1O2RPXBbT0mooh4DYKjA_jp-RLM
     */
    function decreaseSellPositionAmount(
        TuiChainToken _token,
        uint256 _decreaseAmount
        ) external
    {
        // checks

        require(allowedTokens[_token]);
        require(_decreaseAmount > 0);

        SellPosition storage position = sellPositions[_token][msg.sender];

        require(position.amountTokens > 0, "sell position does not exist");
        require(_decreaseAmount <= position.amountTokens);

        // effects

        position.amountTokens = position.amountTokens.sub(_decreaseAmount);

        if (position.amountTokens == 0)
            position.priceNanoDaiPerToken = 0; // free up storage

        // interactions

        _token.safeTransfer({ to: msg.sender, value: _decreaseAmount });
    }

    /**
     * Update the price of an existing sell position.
     */
    function updateSellPositionPrice(
        TuiChainToken _token,
        uint256 _newPriceAttoDaiPerToken
        ) external
    {
        // checks

        require(allowedTokens[_token]);

        SellPosition storage position = sellPositions[_token][msg.sender];

        require(position.amountTokens > 0, "sell position does not exist");

        uint256 newPriceNanoDaiPerToken = _attoDaiToPositiveWholeNanoDai({
            _attoDai: _newPriceAttoDaiPerToken
            });

        // effects

        position.priceNanoDaiPerToken = newPriceNanoDaiPerToken;
    }

    /**
     * Purchase tokens offered by a sell position.
     *
     * The amount and price must be specified to ensure that they are what the
     * user expects, since the sell position can be altered at any time.
     */
    function buy(
        TuiChainToken _token,
        address _seller,
        uint256 _amountTokens,
        uint256 _priceAttoDaiPerToken
        ) external
    {
        // checks

        require(allowedTokens[_token]);

        SellPosition storage position = sellPositions[_token][_seller];

        require(position.amountTokens > 0, "sell position does not exist");

        uint256 priceNanoDaiPerToken = _attoDaiToPositiveWholeNanoDai({
            _attoDai: _priceAttoDaiPerToken
            });

        require(position.amountTokens == _amountTokens);
        require(position.priceNanoDaiPerToken == priceNanoDaiPerToken);

        // effects

        delete sellPositions[_token][_seller];

        uint256 priceAttoDai = _priceAttoDaiPerToken.mul(_amountTokens);
        uint256 feeAttoDai   = feeAttoDaiPerNanoDai.mul(priceAttoDai.div(1e9));

        emit Transaction({
            token: _token,
            seller: _seller,
            buyer: msg.sender,
            amountTokens: _amountTokens,
            priceAttoDaiPerToken: _priceAttoDaiPerToken,
            feeAttoDai: feeAttoDai
            });

        // interactions

        dai.safeTransferFrom({
            from: msg.sender,
            to: _seller,
            value: priceAttoDai
            });

        dai.safeTransferFrom({
            from: msg.sender,
            to: feeRecipient,
            value: feeAttoDai
            });

        _token.safeTransfer({ to: msg.sender, value: _amountTokens });
    }
}

/* -------------------------------------------------------------------------- */
