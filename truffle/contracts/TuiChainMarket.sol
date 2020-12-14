// SPDX-License-Identifier: UNLICENSED
/* -------------------------------------------------------------------------- */

pragma solidity ^0.6.0;

import "./TuiChainMarketLib.sol";
import "./TuiChainToken.sol";

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/math/SafeMath.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";

/* -------------------------------------------------------------------------- */

/** Implements all token market functionality. */
contract TuiChainMarket is Ownable {
    using SafeERC20 for IERC20;
    using SafeERC20 for TuiChainToken;
    using SafeMath for uint256;
    using TuiChainMarketLib for TuiChainMarketLib.SellPositions;

    /* ---------------------------------------------------------------------- */

    /**
     * Emitted whenever the purchase fee is updated.
     *
     * @param previousFeeAttoDaiPerNanoDai The previous purchase fee, in
     *     atto-Dai per nano-Dai
     * @param newFeeAttoDaiPerNanoDai The new purchase fee, in atto-Dai per
     *     nano-Dai
     */
    event FeeUpdated(
        uint256 previousFeeAttoDaiPerNanoDai,
        uint256 newFeeAttoDaiPerNanoDai
    );

    /**
     * Emitted whenever tokens are purchased.
     *
     * @param token The ERC-20 contract implementing the token that was
     *     purchased
     * @param seller The address of the seller
     * @param buyer The address of the buyer
     * @param amountTokens The number of tokens that were purchased
     * @param priceAttoDaiPerToken The value paid by the buyer to the seller for
     *     each token (excluding fees), in atto-Dai
     * @param totalFeeAttoDai The total fee paid by the buyer, in atto-Dai
     */
    event TokensPurchased(
        TuiChainToken token,
        address seller,
        address buyer,
        uint256 amountTokens,
        uint256 priceAttoDaiPerToken,
        uint256 totalFeeAttoDai
    );

    /* ---------------------------------------------------------------------- */

    /** The Dai contract. */
    IERC20 public immutable dai;

    /** Address to which to send all collected fees. */
    address public immutable feeRecipient;

    /** Purchase fee, in atto-Dai per nano-Dai. */
    uint256 public feeAttoDaiPerNanoDai;

    /**
     * Maps an address to true if and only if it is the ERC-20 contract of a
     * token that may be put up for sale and purchased.
     */
    mapping(TuiChainToken => bool) public tokenIsAllowed;

    /** @dev Existing sell positions. */
    TuiChainMarketLib.SellPositions private sellPositions;

    /* ---------------------------------------------------------------------- */

    /**
     * Construct a TuiChainMarket.
     *
     * @param _dai The Dai contract
     * @param _feeRecipient Address of account or contract to which fees are to
     *     be transferred
     * @param _feeAttoDaiPerNanoDai Purchase fee, in atto-Dai per nano-Dai
     */
    constructor(
        IERC20 _dai,
        address _feeRecipient,
        uint256 _feeAttoDaiPerNanoDai
    ) public {
        require(_dai != IERC20(0), "_dai is the zero address");

        require(
            _feeRecipient != address(0),
            "_feeRecipient is the zero address"
        );

        dai = _dai;

        feeRecipient = _feeRecipient;
        feeAttoDaiPerNanoDai = _feeAttoDaiPerNanoDai;
    }

    /* ---------------------------------------------------------------------- */

    /**
     * Ensure that the given value, which is expected to be in atto-Dai, is
     * positive and a multiple of 10^9, i.e., represents a positive multiple of
     * 1 nano-Dai, and return the given value converted to nano-Dai.
     *
     * @param _attoDai The input value, in atto-Dai
     *
     * @return _nanoDai The output value, in nano-Dai
     */
    function _attoDaiToPositiveWholeNanoDai(uint256 _attoDai)
        private
        pure
        returns (uint256 _nanoDai)
    {
        require(
            _attoDai > 0 && _attoDai.mod(1e9) == 0,
            "not a positive multiple of 1 nano-Dai"
        );

        return _attoDai.div(1e9);
    }

    /* ---------------------------------------------------------------------- */

    /**
     * Add the given token to the set of allowed tokens.
     *
     * Has no effect if the token is already in the set of allowed tokens.
     *
     * Only the owner can invoke this function.
     *
     * @param _token The token to add to the set of allowed tokens
     */
    function addToken(TuiChainToken _token) external onlyOwner {
        require(_token != TuiChainToken(0), "_token is the zero address");

        tokenIsAllowed[_token] = true;
    }

    /**
     * Remove the given token from the set of allowed tokens.
     *
     * Has no effect if the token is not in the set of allowed tokens.
     *
     * Only the owner can invoke this function.
     *
     * @param _token The token to remove from the set of allowed tokens
     */
    function removeToken(TuiChainToken _token) external onlyOwner {
        require(_token != TuiChainToken(0), "_token is the zero address");

        tokenIsAllowed[_token] = false;
    }

    /**
     * Set the purchase fee to the given value.
     *
     * Only the owner can invoke this function.
     *
     * @param _feeAttoDaiPerNanoDai The new purchase fee, in atto-Dai per
     *     nano-Dai
     */
    function setFee(uint256 _feeAttoDaiPerNanoDai) external onlyOwner {
        emit FeeUpdated({
            previousFeeAttoDaiPerNanoDai: feeAttoDaiPerNanoDai,
            newFeeAttoDaiPerNanoDai: _feeAttoDaiPerNanoDai
        });

        feeAttoDaiPerNanoDai = _feeAttoDaiPerNanoDai;
    }

    /* ---------------------------------------------------------------------- */

    /**
     * Return the number of existing sell positions.
     *
     * @return _numSellPositions The number of existing sell positions
     */
    function numSellPositions()
        external
        view
        returns (uint256 _numSellPositions)
    {
        return sellPositions.count();
    }

    /**
     * Return the fields of the sell position at the given index.
     *
     * Note that sell positions are stored in an unspecified order.
     *
     * @param _index The index of the sell position
     *
     * @return _token The ERC-20 contract implementing the token that is up for
     *     sale
     * @return _seller The address of the account or contract that put the
     *     tokens up for sale
     * @return _amountTokens The amount of tokens that are up for sale
     * @return _priceAttoDaiPerToken The selling price, in atto-Dai per token
     */
    function sellPositionAt(uint256 _index)
        external
        view
        returns (
            TuiChainToken _token,
            address _seller,
            uint256 _amountTokens,
            uint256 _priceAttoDaiPerToken
        )
    {
        TuiChainMarketLib.SellPosition storage position =
            sellPositions.at({_index: _index});

        _token = position.token;
        _seller = position.seller;
        _amountTokens = position.amountTokens;
        _priceAttoDaiPerToken = position.priceNanoDaiPerToken.mul(1e9);
    }

    /**
     * Return the token amount and price of the sell position with the given
     * token and seller.
     *
     * @param _token The sell position's token
     * @param _seller The sell position's seller
     *
     * @return _amountTokens The amount of tokens that are up for sale
     * @return _priceAttoDaiPerToken The selling price, in atto-Dai per token
     */
    function getSellPosition(TuiChainToken _token, address _seller)
        external
        view
        returns (uint256 _amountTokens, uint256 _priceAttoDaiPerToken)
    {
        TuiChainMarketLib.SellPosition storage position =
            sellPositions.get({_token: _token, _seller: _seller});

        _amountTokens = position.amountTokens;
        _priceAttoDaiPerToken = position.priceNanoDaiPerToken.mul(1e9);
    }

    /**
     * Create a sell position with the message sender as the seller.
     *
     * A sell position of the same token by the same seller must not already
     * exist.
     *
     * @param _token The ERC-20 contract implementing the token to be put up for
     *     sale
     * @param _amountTokens The amount of tokens to put up for sale
     * @param _priceAttoDaiPerToken The selling price, in atto-Dai per token
     */
    function createSellPosition(
        TuiChainToken _token,
        uint256 _amountTokens,
        uint256 _priceAttoDaiPerToken
    ) external {
        // checks

        require(tokenIsAllowed[_token], "_token not allowed by the market");

        require(
            !sellPositions.exists({_token: _token, _seller: msg.sender}),
            "sell position already exists"
        );

        require(_amountTokens > 0, "_amountTokens is zero");

        uint256 priceNanoDaiPerToken =
            _attoDaiToPositiveWholeNanoDai({_attoDai: _priceAttoDaiPerToken});

        // effects

        sellPositions.add({
            _token: _token,
            _seller: msg.sender,
            _amountTokens: _amountTokens,
            _priceNanoDaiPerToken: priceNanoDaiPerToken
        });

        // interactions

        _token.safeTransferFrom({
            from: msg.sender,
            to: address(this),
            value: _amountTokens
        });
    }

    /**
     * Remove a sell position whose seller is the message sender.
     *
     * @dev This function does not check if the token is allowed in order to
     *     permit sellers to remove sell positions of tokens that were but are
     *     no longer allowed
     *
     * @param _token The ERC-20 contract implementing the token whose sell
     *     position to remove
     */
    function removeSellPosition(TuiChainToken _token) external {
        // checks

        require(
            sellPositions.exists({_token: _token, _seller: msg.sender}),
            "sell position does not exist"
        );

        // effects

        TuiChainMarketLib.SellPosition storage position =
            sellPositions.get({_token: _token, _seller: msg.sender});

        uint256 amountTokens = position.amountTokens;

        sellPositions.remove({_token: _token, _seller: msg.sender});

        // interactions

        _token.safeTransfer({to: msg.sender, value: amountTokens});
    }

    /**
     * Increase the token amount of an existing sell position.
     *
     * @dev Functions are provided to increase and decrease the sell position
     *     amount instead of having a single function to set it to a given value
     *     in order to avoid attacks analogous to ERC-20's multiple withdrawal
     *     attack
     *
     * @param _token The ERC-20 contract implementing the token whose sell
     *     position to update
     * @param _increaseAmount By how much to increase the sell position's token
     *     amount
     */
    function increaseSellPositionAmount(
        TuiChainToken _token,
        uint256 _increaseAmount
    ) external {
        // checks

        require(tokenIsAllowed[_token], "_token not allowed by the market");
        require(_increaseAmount > 0, "_increaseAmount is zero");

        require(
            sellPositions.exists({_token: _token, _seller: msg.sender}),
            "sell position does not exist"
        );

        // effects

        TuiChainMarketLib.SellPosition storage position =
            sellPositions.get({_token: _token, _seller: msg.sender});

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
     * If _decreaseAmount equals the amount of tokens currently up for sale, the
     * sell position is removed.
     *
     * @dev Functions are provided to increase and decrease the sell position
     *     amount instead of having a single function to set it to a given value
     *     in order to avoid attacks analogous to ERC-20's multiple withdrawal
     *     attack
     *
     * @param _token The ERC-20 contract implementing the token whose sell
     *     position to update
     * @param _decreaseAmount By how much to decrease the sell position's token
     *     amount
     */
    function decreaseSellPositionAmount(
        TuiChainToken _token,
        uint256 _decreaseAmount
    ) external {
        // checks

        require(tokenIsAllowed[_token], "_token not allowed by the market");
        require(_decreaseAmount > 0, "_decreaseAmount is zero");

        require(
            sellPositions.exists({_token: _token, _seller: msg.sender}),
            "sell position does not exist"
        );

        TuiChainMarketLib.SellPosition storage position =
            sellPositions.get({_token: _token, _seller: msg.sender});

        require(
            _decreaseAmount <= position.amountTokens,
            "_decreaseAmount exceeds amount for sale"
        );

        // effects

        position.amountTokens = position.amountTokens.sub(_decreaseAmount);

        if (position.amountTokens == 0)
            sellPositions.remove({_token: _token, _seller: msg.sender});

        // interactions

        _token.safeTransfer({to: msg.sender, value: _decreaseAmount});
    }

    /**
     * Update the token price of an existing sell position.
     *
     * @param _token The ERC-20 contract implementing the token whose sell
     *     position to update
     * @param _newPriceAttoDaiPerToken The new selling price, in atto-Dai per
     *     token
     */
    function updateSellPositionPrice(
        TuiChainToken _token,
        uint256 _newPriceAttoDaiPerToken
    ) external {
        // checks

        require(tokenIsAllowed[_token], "_token not allowed by the market");

        require(
            sellPositions.exists({_token: _token, _seller: msg.sender}),
            "sell position does not exist"
        );

        uint256 newPriceNanoDaiPerToken =
            _attoDaiToPositiveWholeNanoDai({
                _attoDai: _newPriceAttoDaiPerToken
            });

        // effects

        TuiChainMarketLib.SellPosition storage position =
            sellPositions.get({_token: _token, _seller: msg.sender});

        position.priceNanoDaiPerToken = newPriceNanoDaiPerToken;
    }

    /**
     * Purchase tokens offered by a sell position.
     *
     * A sell position of the given token by the given seller must exist,
     * _amountTokens must not exceed the amount of tokens offered by that sell
     * position, and _priceAttoDaiPerToken and _feeAttoDaiPerNanoDai must
     * respectively match the sell position's price and the purchase fee.
     *
     * @dev The price and fee must be specified int order to ensure that it is
     *     what the user expects, since the actual fee and sell position price
     *     can be updated at any time
     *
     * @param _token The ERC-20 contract implementing the token to be purchased
     * @param _amountTokens The amount of tokens to purchase
     * @param _priceAttoDaiPerToken The selling price, in atto-Dai per token
     * @param _feeAttoDaiPerNanoDai The purchase fee, in atto-Dai per token
     */
    function purchase(
        TuiChainToken _token,
        address _seller,
        uint256 _amountTokens,
        uint256 _priceAttoDaiPerToken,
        uint256 _feeAttoDaiPerNanoDai
    ) external {
        // checks

        require(tokenIsAllowed[_token], "_token not allowed by the market");
        require(_amountTokens > 0, "_amountTokens is zero");

        require(
            sellPositions.exists({_token: _token, _seller: _seller}),
            "sell position does not exist"
        );

        uint256 priceNanoDaiPerToken =
            _attoDaiToPositiveWholeNanoDai({_attoDai: _priceAttoDaiPerToken});

        TuiChainMarketLib.SellPosition storage position =
            sellPositions.get({_token: _token, _seller: _seller});

        require(
            _amountTokens <= position.amountTokens,
            "_amountTokens exceeds amount for sale"
        );

        require(
            priceNanoDaiPerToken == position.priceNanoDaiPerToken,
            "_priceAttoDaiPerToken does not match the current price"
        );

        require(
            _feeAttoDaiPerNanoDai == feeAttoDaiPerNanoDai,
            "_feeAttoDaiPerNanoDai does not match the current fee"
        );

        // effects

        position.amountTokens = position.amountTokens.sub(_amountTokens);

        if (position.amountTokens == 0)
            sellPositions.remove({_token: _token, _seller: _seller});

        uint256 priceAttoDai = _priceAttoDaiPerToken.mul(_amountTokens);
        uint256 feeAttoDai = feeAttoDaiPerNanoDai.mul(priceAttoDai.div(1e9));

        emit TokensPurchased({
            token: _token,
            seller: _seller,
            buyer: msg.sender,
            amountTokens: _amountTokens,
            priceAttoDaiPerToken: _priceAttoDaiPerToken,
            totalFeeAttoDai: feeAttoDai
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

        _token.safeTransfer({to: msg.sender, value: _amountTokens});
    }
}

/* -------------------------------------------------------------------------- */
