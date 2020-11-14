// SPDX-License-Identifier: MIT
pragma solidity >=0.6.0;

import "@openzeppelin/contracts/math/SafeMath.sol";
import "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";
import "../DebtToken.sol";

contract Marketplace {
  using SafeMath for uint256;
  using SafeERC20 for DebtToken;

  //Structure for sell position
  struct sellPosition{
    uint256 amount; //tokens that can be selled
    uint256 sellPrice; //sell price per token in wei
    uint256 minAmountToBuy; //minimum amount of tokens for someone to buy
    address ownerAddress;
    bool    exists;
  }

  //Map of selling positions, quantity -> sellPrice(wei)
  mapping(address => mapping( address => sellPosition)) sellPositions;

  function createSellPosition(DebtToken token, uint256 _sellPrice, uint256 _minAmountToBuy, uint256 _amount) public {
    //Check if the seller has sufficient tokens to sell
    require(token.balanceOf(msg.sender) >= _amount);

    //Save sellPosition
    sellPositions[msg.sender][token.address] = sellPosition(_amount, _sellPrice, _minAmountToBuy, msg.address, true);
  }

  function buyTokens(DebtToken token, address seller, uint256 amountToBuy) public payable {
    sellPosition memory sellP = sellPositions[seller][token.address];
    
    //Check if the tokens are listed for selling and are enough
    require(sellP.exists && sellP.amount >= amountToBuy);
    
    //Check if the amount is greater than the minimum amount
    require(sellP.minAmountToBuy <= amountToBuy);

    //Check if the value is correct
    require(msg.value == amountToBuy.mul(sellP.sellPrice));

    //Transfer tokens
    token.manualTransfer(seller, msg.sender, amountToBuy);

    //Transfer ETH to the seller
    sellP.ownerAddress.sender.transfer(msg.value);
  }

  //TODO: Save sell positions to database

  function endSellPostion(DebtToken token) public {
    sellPosition memory sellP = sellPositions[msg.sender][token.address];

    //Check if sell position exists
    require(sellP.exists);

    //Delete sell position
    delete sellP;
  }
}
