/* -------------------------------------------------------------------------- */

const TuiChainController = artifacts.require("TuiChainController");
const TuiChainLoan       = artifacts.require("TuiChainLoan");
const TuiChainToken      = artifacts.require("TuiChainToken");

const DaiMock = artifacts.require("DaiMock");

const {
  constants,    // Common constants, like the zero address and largest integers
  expectRevert, // Assertions for transactions that should fail
} = require('@openzeppelin/test-helpers');  

// Imports our helpers
var { fundsToInt } = require('./helpers');

// Mocks an ENUM identical to the one in the TuiChainLoan
const Phase = Object.freeze({"Funding":0, "Expired":1, "Canceled":2, "Active":3, "Finalized":4})

/* -------------------------------------------------------------------------- */

// Sequence of tests for the Loan Contract
// This tests represent possible interactions from the backend with loan contract
contract("Loan", function (accounts) {


  // market fee, is equivalent to 10% of a DAI
  const marketFeeAttoDaiPerNanoDai = BigInt(10) ** BigInt(8);

  /* -------------------------------------------------------------------------- */

  // variable which represents the deployed DAI mock
  let daiMock = null;

  // variable which represents the deployed controller contract
  let tuiChainController = null;

  // variable which represents the a deployed loan contract
  let tuiChainLoan = null;

  // variable which represents the loan object
  let loanObject = null;

  // variable which represents the funds provided from account 3, also represent the amount of TuiChainTokens received
  let providedFunds = null;

  // variable which represents the fee for each funding movement
  let fundingFee = null;

  // variable which represents the payment for each funding movement
  let paymentFee = null;
  /* -------------------------------------------------------------------------- */

  // runs once before the first test
  before( async () => {

    // deploy contract which mocks DAI contract
    daiMock = await DaiMock.new();

    // loan specs
    fundingFee = 0.1
    paymentFee = 0.1
    loanObject = {
      _feeRecipient: accounts[0],
      _loanRecipient: accounts[1],
      _secondsToExpiration: 60, // 1 minute
      _fundingFeeAttoDaiPerDai: BigInt(fundingFee * 100) ** BigInt(17), // 10% fee
      _paymentFeeAttoDaiPerDai: BigInt(paymentFee * 100) ** BigInt(17), // 10% fee
      _requestedValueAttoDai: BigInt(1000) * (BigInt(10) ** BigInt(18)) // 1000 DAI
    };

    // deploy controller contract
    tuiChainController = await TuiChainController
      .new(
        daiMock.address,
        accounts[0],
        marketFeeAttoDaiPerNanoDai
      );

    // get loan contract from an address with at() function
    const transaction = await tuiChainController.createLoan(...Object.values(loanObject));
    tuiChainLoan      = await TuiChainLoan.at(transaction.logs[0].address);

    // get token  contract from an address with at() functions
    tuiChainToken = await TuiChainToken.at(await tuiChainLoan.token());

    // start every account with 1200 DAI
    accounts.forEach( account => {
      daiMock.mint(account, BigInt(1200) * (BigInt(10) ** BigInt(18)));
    });

    // Allows tokens to be transfer to our contracts
    providedFunds = 1000;
    await daiMock.increaseAllowance(
      tuiChainLoan.address, BigInt(2000) * (BigInt(10) ** BigInt(18)), 
      {from: accounts[2]}
    );
    await daiMock.increaseAllowance(
      tuiChainLoan.address, BigInt(2000) * (BigInt(10) ** BigInt(18)), 
      {from: accounts[1]}
    );
  });

  /* -------------------------------------------------------------------------- */

  it("Fails to provide more funds that those who were requested for loan", async function () {
    await expectRevert.unspecified(
      tuiChainLoan.provideFunds(BigInt(2000) * (BigInt(10) ** BigInt(18)), {from: accounts[2]})
    );
  });

  //funds to provide initially (usefull in another test)
  let fundsToProvide = null;
  it("Provides funds to the loan", async function () {
    fundsToProvide             = 100;
    const initialInvestorFunds = fundsToInt(await daiMock.balanceOf(accounts[2]));

    await tuiChainLoan
      .provideFunds(
        BigInt(fundsToProvide) * (BigInt(10) ** BigInt(18)),
        {from: accounts[2]})
      ;
    const fundedDai          = fundsToInt(await tuiChainLoan.fundedValueAttoDai());
    const finalInvestorFunds = fundsToInt(await daiMock.balanceOf(accounts[2]));
    
    assert(finalInvestorFunds == initialInvestorFunds - (fundsToProvide * (1 + fundingFee)));
    assert(fundedDai == fundsToProvide);
  });

  it("Fails to withdraw more funds than those who were provided", async function () {
    await expectRevert.unspecified(
      tuiChainLoan.withdrawFunds(
        BigInt(fundsToProvide + 1) * (BigInt(10) ** BigInt(18)),
        {from: accounts[2]}
      )
    );
  });

  it("Withdraws the provided funds", async function () {
    const initialInvestorFunds = fundsToInt(await daiMock.balanceOf(accounts[2]));

    await tuiChainToken
      .increaseAllowance(
        tuiChainLoan.address,
        BigInt(fundsToProvide) * (BigInt(10) ** BigInt(18)),
        {from: accounts[2]}
      );
    await tuiChainLoan
      .withdrawFunds(
        BigInt(fundsToProvide) * (BigInt(10) ** BigInt(18)),
        {from: accounts[2]}
      );
    const fundedDai          = fundsToInt(await tuiChainLoan.fundedValueAttoDai());
    const finalInvestorFunds = fundsToInt(await daiMock.balanceOf(accounts[2]));
    
    assert(fundedDai == 0);
    assert(finalInvestorFunds == initialInvestorFunds + (fundsToProvide * (1 + fundingFee)));
  });

  it("Fails to make payment when phase is not active", async function () {
    await expectRevert.unspecified(
      tuiChainLoan.makePayment(BigInt(100) * (BigInt(10) ** BigInt(18)))
    );
  });

  it("Provides the remaining funds to the loan", async function () {
    const initialStundentFunds = fundsToInt(await daiMock.balanceOf(accounts[1]));
    const initialInvestorFunds = fundsToInt(await daiMock.balanceOf(accounts[2]));

    await tuiChainLoan
      .provideFunds(
        BigInt(providedFunds) * (BigInt(10) ** BigInt(18)),
        {from: accounts[2]}
      );
    const fundedDai          = fundsToInt(await tuiChainLoan.fundedValueAttoDai());
    const phase              = (await tuiChainLoan.phase()).toNumber();
    const finalStundentFunds = fundsToInt(await daiMock.balanceOf(accounts[1]));
    const finalInvestorFunds = fundsToInt(await daiMock.balanceOf(accounts[2]));
    
    assert(fundedDai          == providedFunds);
    assert(phase              == Phase.Active);
    assert(finalStundentFunds == providedFunds + initialStundentFunds);
    assert(finalInvestorFunds == initialInvestorFunds -  (providedFunds * (1 + fundingFee)));
  });

  it("Fails to provide funds for a loan not in funding phase", async function () {
    const phase = (await tuiChainLoan.phase()).toNumber();

    assert(phase != Phase.Funding);
    await expectRevert.unspecified(
      tuiChainLoan.provideFunds(
        BigInt(providedFunds - fundsToProvide) * (BigInt(10) ** BigInt(18)),
        {from: accounts[2]}
      )
    );
  });

  it("Fails to withdraw the provided funds when fase is not 'funding", async function () {
    const phase = (await tuiChainLoan.phase()).toNumber();

    assert(phase != Phase.Funding);
    await expectRevert.unspecified(
      tuiChainLoan.withdrawFunds(
        BigInt(fundsToProvide) * (BigInt(10) ** BigInt(18)),
        {from: accounts[2]}
      )
    );
  });

  it("Makes payment", async function () {
    const paymentAmount           = 1000;
    const initialStudentDaiAmount = fundsToInt(await daiMock.balanceOf(accounts[1]));

    await tuiChainLoan.makePayment(
      BigInt(paymentAmount) * (BigInt(10) ** BigInt(18)),
      {from: accounts[1]}
    );
    const paidValueDai          = fundsToInt(await tuiChainLoan.paidValueAttoDai());
    const finalStudentDaiAmount = fundsToInt(await daiMock.balanceOf(accounts[1]));

    assert(paymentAmount == paidValueDai);
    assert(finalStudentDaiAmount == initialStudentDaiAmount - (paymentAmount * (1 + paymentFee)));
  });

  it("Fails to reedem tokens when fase is not finalized", async function () {
    const phase = (await tuiChainLoan.phase()).toNumber();

    assert(phase != Phase.Finalized);
    await expectRevert.unspecified(
      tuiChainLoan.redeemTokens(
        10,
        {from: accounts[2]}
      )
    );
  });

  it("Fails to reedem tokens when account as no one to reedem", async function () {
    await tuiChainController.finalizeLoan(tuiChainLoan.address);
    const phase = (await tuiChainLoan.phase()).toNumber();

    assert(phase == Phase.Finalized);
    await expectRevert.unspecified(
      tuiChainLoan.redeemTokens(
        10,
        {from: accounts[5]}
      )
    );
  });

  it("Fails to reedem more tokens than the available ones", async function () {
    const phase = (await tuiChainLoan.phase()).toNumber();

    assert(phase == Phase.Finalized);
    await expectRevert.unspecified(
      tuiChainLoan.redeemTokens(
        2000,
        {from: accounts[2]}
      )
    );
  });

  it("Reedems tokens", async function () {
    const phase             = (await tuiChainLoan.phase()).toNumber();
    const initialDaiBalance = fundsToInt(await daiMock.balanceOf(accounts[2]));
    const tokensToRedeem    = 10

    assert(phase == Phase.Finalized);
    await tuiChainLoan.redeemTokens(tokensToRedeem, {from: accounts[2]});

    const finalDaiBalance            = fundsToInt(await daiMock.balanceOf(accounts[2]));
    const redemptionValueDaiPerToken = fundsToInt(await tuiChainLoan.redemptionValueAttoDaiPerToken());

    assert(finalDaiBalance == initialDaiBalance + (redemptionValueDaiPerToken * tokensToRedeem));
  });
})
