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

  // how many wei an investor gets per token
  uint256 public paybackRate;

  // start and end timestamps where investments are allowed 
  uint256 internal startTime;
  uint256 internal endTime;


  //=======================
  // Constructor
  //=======================

  constructor (uint256 _startTime, uint256 _endTime, uint256 _rate, DebtToken _token) 
    State() public {

    require(ValidationLibrary.validContractCreation(_startTime, _endTime, _rate, _token));

    token = _token;
    wallet = msg.sender;
    rate = _rate;
    paybackRate = 0;
    startTime = _startTime;
    endTime = _endTime;

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

    // refund
    msg.sender.transfer(refundWei);

    // send event
    TokenCancelation(msg.sender, refundWei, _tokens);

  }

  // function for cancel all token acquired
  function cancelAcquisition() public isSaleOrCanceledState {

    // get number of tokens
    uint256 tokens = token.balanceOf(msg.sender);

    cancelAcquisition(tokens);

  }

  // raise funds to give'em to the proper student
  function raiseFunds() public onlyOwner isActiveState {
    
    uint256 amount = address(this).balance;

    // transfer to the owner's wallet
    wallet.transfer(amount);

    // event
    FundsRaised(wallet, amount);

  }

  // CAUTION:
  // WE SHOULD APPLY TAXES HERE
  function payback() public payable isActiveState {

    // event
    Payback(msg.sender, msg.value);
    
  }

  // allow investors to redeem tokens and receive their part back in ETH
  function redeemTokens() public isRedeemableState {
    
    // get amount of tokens
    uint256 tokenAmount = token.balanceOf(msg.sender);

    // calculate the wei to receive
    uint256 weiAmount = tokenAmount.mul(paybackRate);

    // transfer tokens to the original wallet
    token.manualTransfer(msg.sender, wallet, tokenAmount);

    // send the ETH to investor
    msg.sender.transfer(weiAmount);

    // event
    TokenRedeem(msg.sender, weiAmount, tokenAmount);

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
  function transitionToRedeemable(uint256 _paybackRate) public onlyOwner isActiveState {

    // set the value per token
    paybackRate = _paybackRate;

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
  * @param purchaser who want money back
  * @param value weis refunded
  * @param amount amount of tokens canceled
  */
  event TokenCancelation(address indexed purchaser, uint256 value, uint256 amount);

  /**
  * event for raise funds
  * @param borrower who want money back
  * @param value weis received
  */
  event FundsRaised(address indexed borrower, uint256 value);

  /**
  * event for raise funds
  * @param payer who pay money back
  * @param value weis paied
  */
  event Payback(address indexed payer, uint256 value);
  
  /**
  * event for token redeem
  * @param purchaser who want money back
  * @param value weis received
  * @param amount amount of tokens redeemed
  */
  event TokenRedeem(address indexed purchaser, uint256 value, uint256 amount);

}
