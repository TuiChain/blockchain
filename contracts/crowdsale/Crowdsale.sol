// SPDX-License-Identifier: MIT
pragma solidity >=0.6.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/math/SafeMath.sol";
import "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "../DebtToken.sol";
import "./State.sol";

import { ValidationLibrary } from "../libraries/ValidationLibrary.sol";

contract Crowdsale is Ownable, State {

  using SafeMath for uint256;
  using SafeERC20 for DebtToken;

  //=======================
  // Variables & constants
  //=======================

  // The token being sold
  DebtToken public token;

  // address where funds are collected
  address payable public wallet;

  // how many token units a buyer gets per wei
  uint256 public rate;

  // amount of raised money in wei
  uint256 public weiRaised;

  //=======================
  // Constructor
  //=======================

  constructor (uint256 _startTime, uint256 _endTime, uint256 _rate, DebtToken _token) 
    State(_startTime, _endTime)
    public 
  {
    require(ValidationLibrary.validContractCreation(_startTime, _endTime, _rate, _token));

    rate = _rate;
    wallet = msg.sender;
    token = _token;
  }

  //=======================
  // Functions
  //=======================

  // function for acquiring some tokens
  // only possible in sale state
  function acquireTokens() public payable isSaleState {

    // verifications
    require(ValidationLibrary.validPurchase(msg.value, msg.sender));

    uint256 weiAmount = msg.value;

    // calculate token amount to be created
    uint256 tokens = weiAmount.mul(rate);

    // update state
    weiRaised = weiRaised.add(weiAmount);

    // safe transfer of tokens
    token.safeTransferFrom(wallet, msg.sender, tokens);
    
    // send event
    TokenAcquisition(msg.sender, weiAmount, tokens);
    
    // transfer ETH to wallet
    wallet.transfer(msg.value);
    
  }

  // function for cancel token acquisition
  // only possible in sale state
  function cancelAcquisition() public isSaleState {

    // get number of tokens
    uint256 tokens = token.balanceOf(msg.sender);

    // wei to refund
    uint256 refundWei = tokens.div(rate);

    // safe transfer of tokens
    token.safeTransferFrom(msg.sender, wallet, tokens);

    // send event
    TokenCancelation(msg.sender, refundWei, tokens);

    // refund
    msg.sender.transfer(refundWei);

  }

  // function call by the owner, to cancel the crowdsale
  // only possible in sale state
  function cancelCrowdsale() public onlyOwner isSaleState {

    // validation
    require(ValidationLibrary.hasEnded(endTime));

    // do some things

  }




  //=======================
  // Fallback
  //=======================

  // fallback function can be used to buy tokens
  receive() external payable {
    // buyTokens(msg.sender);
  }

  //=======================
  // Events
  //=======================

  /**
  * event for token aquisition
  * @param purchaser who paid for the tokens
  * @param value weis paid for purchase
  * @param amount amount of tokens acquired
  */
  event TokenAcquisition(address indexed purchaser, uint256 value, uint256 amount);

  /**
  * event for token cancelation
  * @param purchaser who want monay back
  * @param value weis refunded
  * @param amount amount of tokens canceled
  */
  event TokenCancelation(address indexed purchaser, uint256 value, uint256 amount);
  
}
