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
  function acquireTokens() public payable isSaleState {

    // verifications
    require(ValidationLibrary.validPurchase(msg.value, msg.sender));

    uint256 weiAmount = msg.value;

    // calculate token amount to be created
    uint256 tokens = weiAmount.mul(rate);
    uint256 possibleTokens = token.balanceOf(wallet);
    uint256 amount = tokens >= possibleTokens ? possibleTokens : tokens;

    // safe transfer of tokens
    token.manualTransfer(wallet, msg.sender, amount);

    // in case of impossibility of buying the correspondent tokens
    // give the extra ETH back
    if (amount < tokens) {
      weiAmount = (tokens-amount).div(rate);
      msg.sender.transfer(weiAmount);
    }
    
    // send event
    TokenAcquisition(msg.sender, weiAmount, amount);
    
    // transfer ETH to contract
    address(this).transfer(msg.value);
    
  }

  // function for cancel some of the tokens acquired
  function cancelAcquisition(uint256 _tokens) public isSaleOrCanceledState {

    // get number of tokens
    uint256 nTokens = token.balanceOf(msg.sender);

    // validation
    require(_tokens <= nTokens);

    // wei to refund
    uint256 refundWei = _tokens.div(rate);

    // safe transfer of tokens
    token.manualTransfer(msg.sender, wallet, _tokens);

    // send event
    TokenCancelation(msg.sender, refundWei, _tokens);

    // refund
    msg.sender.transfer(refundWei);

  }

  // function for cancel all token acquired
  function cancelAcquisition() public isSaleOrCanceledState {

    // get number of tokens
    uint256 tokens = token.balanceOf(msg.sender);

    cancelAcquisition(tokens);

  }

  // raise funds to give'em to the proper student
  function raiseFunds() public onlyOwner isActiveState {
    
    // transfer to the owner's wallet
    wallet.transfer(address(this).balance);

  }

  // CAUTION:
  // WE SHOULD APPLY TAXES HERE
  function payback() public payable isActiveState {

    address(this).transfer(msg.value);
    
  }


  //=======================
  // State Transitions
  //=======================

  // function call by the owner, to activate the crowdsale
  function transitionToActive() public onlyOwner isSaleState {

    // validation
    require(token.balanceOf(msg.sender) == 0);

    // set state
    setState(StateEnum.ACTIVE);

  }

  // function call by the owner, to set the crowdsale to redeemable state
  function transitionToRedeemable() public onlyOwner isActiveState {

    // set state
    setState(StateEnum.REDEEMABLE);

  }

  // function call by the owner, to cancel the crowdsale
  function cancelCrowdsale() public onlyOwner isSaleState {

    // validation
    require(ValidationLibrary.hasEnded(endTime));

    // set state
    setState(StateEnum.CANCELED);

  }


  //=======================
  // Fallback
  //=======================

  // fallback function can be used to buy tokens
  receive() external payable {
    
    // buyTokens(msg.sender);
    acquireTokens();

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
