// SPDX-License-Identifier: UNLICENSED
/* -------------------------------------------------------------------------- */

pragma solidity ^0.6.0;

import "./TuiChainToken.sol";

import "@openzeppelin/contracts/math/SafeMath.sol";

/* -------------------------------------------------------------------------- */

/**
 * Implements a data structure to store sell positions, allowing lookup by
 * token-seller pairs and iteration.
 */
library TuiChainMarketLib
{
    using SafeMath for uint256;

    /* ---------------------------------------------------------------------- */

    /**
     * Represents a sell position of a specific token by a specific seller.
     *
     * @param token The ERC-20 contract implementing the token that is up for
     *     sale
     * @param seller The address of the account or contract that put the tokens
     *     up for sale
     * @param amountTokens The amount of tokens that are up for sale
     * @param priceNanoDaiPerToken The selling price, in nano-Dai per token
     */
    struct SellPosition
    {
        TuiChainToken token;
        address seller;

        uint256 amountTokens;
        uint256 priceNanoDaiPerToken;
    }

    /**
     * @param values Existing sell positions, in no particular order
     * @param indices For all existing sell positions, maps the respective token
     *     and seller address to the index of that sell position in the
     *     sellPositions array, incremented by one; maps token and seller
     *     addresses that don't correspond to an existing sell position to zero
     */
    struct SellPositions
    {
        SellPosition[] values;
        mapping(TuiChainToken => mapping(address => uint256)) indices;
    }

    /* ---------------------------------------------------------------------- */

    /**
     * Return the number of existing sell positions.
     *
     * @return _count The number of existing sell positions
     */
    function count(SellPositions storage _self)
        internal view returns (uint256 _count)
    {
        return _self.values.length;
    }

    /**
     * Return the sell position at the given index.
     *
     * Note that sell positions are stored in an unspecified order.
     *
     * @param _index The index of the sell position
     * @return _position The sell position
     */
    function at(SellPositions storage _self, uint256 _index)
        internal view returns (SellPosition storage _position)
    {
        return _self.values[_index];
    }

    /**
     * Check whether a sell position with the given token and seller exists.
     *
     * @param _token The sell position's token
     * @param _seller The sell position's seller
     * @return _exists Whether a sell position with the given token and seller
     *     exists
     */
    function exists(
        SellPositions storage _self,
        TuiChainToken _token,
        address _seller
        ) internal view returns (bool _exists)
    {
        return _self.indices[_token][_seller] != 0;
    }

    /**
     * Return the sell position with the given token and seller.
     *
     * @param _token The sell position's token
     * @param _seller The sell position's seller
     * @return _position The sell position with the given token and seller
     */
    function get(
        SellPositions storage _self,
        TuiChainToken _token,
        address _seller
        ) internal view returns (SellPosition storage _position)
    {
        return _self.values[_self.indices[_token][_seller].sub(1)];
    }

    /**
     * Add a sell position.
     *
     * No sell position with the given token and seller may exist.
     *
     * @param _token The sell position's token
     * @param _seller The sell position's seller
     * @param _amountTokens The sell position's amount of tokens
     * @param _priceNanoDaiPerToken The sell position's token price, in nano-Dai
     *     per token
     */
    function add(
        SellPositions storage _self,
        TuiChainToken _token,
        address _seller,
        uint256 _amountTokens,
        uint256 _priceNanoDaiPerToken
        ) internal
    {
        require(_self.indices[_token][_seller] == 0, "sell position exists");

        // add position to array of all positions

        _self.values.push(
            SellPosition({
                token: _token,
                seller: _seller,
                amountTokens: _amountTokens,
                priceNanoDaiPerToken: _priceNanoDaiPerToken
                })
            );

        // add entry mapping token and seller to index of position + 1

        _self.indices[_token][_seller] = _self.values.length;
    }

    /**
     * Add an existing sell position.
     *
     * Note that this invalidates storage references to the SellPosition being
     * removed.
     *
     * @param _token The sell position's token
     * @param _seller The sell position's seller
     */
    function remove(
        SellPositions storage _self,
        TuiChainToken _token,
        address _seller
        ) internal
    {
        uint256 index = _self.indices[_token][_seller].sub(1);

        SellPosition storage last = _self.values[_self.values.length - 1];

        // replace position to remove with last position in array of positions

        _self.values[index] = last;

        // update mapping entry pertaining to moved position

        _self.indices[last.token][last.seller] = index + 1;

        // remove last position in array of positions

        _self.values.pop();

        // remove mapping entry pertaining to removed position

        delete _self.indices[_token][_seller];
    }
}

/* -------------------------------------------------------------------------- */
