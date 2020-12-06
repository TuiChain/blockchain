/* -------------------------------------------------------------------------- */

const TuiChainController = artifacts.require("TuiChainController");
const TuiChainMarket = artifacts.require("TuiChainMarket");
const TuiChainLoan = artifacts.require("TuiChainLoan");

const DaiMock = artifacts.require("DaiMock");

// Mocks an ENUM identical to the one in the TuiChainLoan
const Phase = Object.freeze({"Funding":0, "Expired":1, "Canceled":2, "Active":3, "Finalized":4})

/* -------------------------------------------------------------------------- */

// Sequence of tests for the deployment and interaction with Controller Contract
// This tests represent possible interactions from the backend with controller contract
contract("Controller Deployment and Interaction", function (accounts) {


  // market fee, is equivalent to 10% of a DAI
  const marketFeeAttoDaiPerNanoDai = BigInt(10) ** BigInt(8);

  /* -------------------------------------------------------------------------- */

  // variable which represents the deployed DAI mock
  let daiMock = null;

  // variable which represents the deployed controller contract
  let tuiChainController = null;

  // variable which represents the deployed market contract
  let tuiChainMarket = null;

  // variable which represents the a deployed loan contract
  let tuiChainLoan = null;

  // variable which represents the loan object
  let loanObject = null;

  /* -------------------------------------------------------------------------- */

  // runs once before the first test
  before( async () => {

    // deploy contract which mocks DAI contract
    daiMock = await DaiMock.new();

    // deploy controller contract
    tuiChainController = await TuiChainController.new(daiMock.address, accounts[0], marketFeeAttoDaiPerNanoDai);

    // get contract from an address with at() function
    tuiChainMarket = await TuiChainMarket.at(await tuiChainController.getMarket());

    // start every account with 1000 DAI
    accounts.forEach( account => {
      daiMock.mint(account, BigInt(1000) * (BigInt(10) ** BigInt(18)));
    });
  
  });

  // runs before every test
  beforeEach( async () => {

    loanObject = {
      _feeRecipient: accounts[0],
      _loanRecipient: accounts[1],
      _secondsToExpiration: 60, // 1 minute
      _fundingFeeAttoDaiPerDai: BigInt(10) ** BigInt(17), // 10% fee
      _paymentFeeAttoDaiPerDai: BigInt(10) ** BigInt(17), // 10% fee
      _requestedValueAttoDai: BigInt(1000) * (BigInt(10) ** BigInt(18)) // 1000 DAI
    };

  });

  /* -------------------------------------------------------------------------- */

  it("Fail to change market fee if not the owner", async function () {

    const newFee = BigInt(2) * (BigInt(10) ** BigInt(8));
    
    try {

      await tuiChainController.setMarketFee(newFee, {from: accounts[1]});

    } catch(e) {

      return assert(e.message.includes('caller is not the owner'));

    }

    return assert(false);

  });

  it("Change market fee to 20% and check it", async function () {

    const newFee = BigInt(2) * (BigInt(10) ** BigInt(8));
    
    await tuiChainController.setMarketFee(newFee);

    return assert((await tuiChainMarket.getFee()).toNumber() == newFee);

  });

  /* -------------------------------------------------------------------------- */

  it("Fail to create loan with 0 address in _feeRecipient", async function () {

    try {

      loanObject._feeRecipient = 0x0000000000000000000000000000000000000000;

      await tuiChainController.createLoan(...Object.values(loanObject));

    } catch(e) {
      
      return assert(e.message.includes('_feeRecipient'));

    }

    return assert(false);

  });

  it("Fail to create loan with 0 address in _loanRecipient", async function () {

    try {

      loanObject._loanRecipient = 0x0000000000000000000000000000000000000000;

      await tuiChainController.createLoan(...Object.values(loanObject));

    } catch(e) {
      
      return assert(e.message.includes('_loanRecipient'));

    }

    return assert(false);

  });

  it("Fail to create loan with negative expiration time", async function () {

    try {

      loanObject._secondsToExpiration = -1;

      await tuiChainController.createLoan(...Object.values(loanObject));

    } catch(e) {
      
      return assert(e.message.includes('_secondsToExpiration'));

    }

    return assert(false);

  });

  it("Fail to create loan with less than a unit of DAI", async function () {

    try {

      loanObject._requestedValueAttoDai = BigInt(10) ** BigInt(17);

      await tuiChainController.createLoan(...Object.values(loanObject));

    } catch(e) {
      
      return assert(e.message.includes('VM Exception while processing transaction: revert'));

    }

    return assert(false);

  });

  it("Fail to create loan without a multiple integer of a unit of DAI", async function () {

    try {

      loanObject._requestedValueAttoDai = BigInt(1.5 * (10 ** 18)); 

      await tuiChainController.createLoan(...Object.values(loanObject));

    } catch(e) {
      
      return assert(e.message.includes('VM Exception while processing transaction: revert'));

    }

    return assert(false);

  });

  it("Fail to create a loan if not the owner", async function () {

    try {
    
      await tuiChainController.createLoan(...Object.values(loanObject), {from: accounts[1]});

    } catch(e) {

      return assert(e.message.includes('caller is not the owner'));

    }

  });
  
  it("Create a loan with a requested DAI value of 1000 DAI", async function () {

    const transaction = await tuiChainController.createLoan(...Object.values(loanObject));

    tuiChainLoan = await TuiChainLoan.at(transaction.logs[0].address);

    return assert((await tuiChainLoan.getToken) != 0x0000000000000000000000000000000000000000);

  });

  /* -------------------------------------------------------------------------- */

  it("Fail to finalize the loan if not the owner", async function () {

    try {

      assert((await tuiChainLoan.checkExpiration.call()) == false);
    
      await tuiChainController.finalizeLoan(tuiChainLoan.address, {from: accounts[1]});

    } catch(e) {

      return assert(e.message.includes('caller is not the owner'));

    }

  });

  it("Fail to finalize loan before it turns Active", async function () {

    try {

      assert((await tuiChainLoan.checkExpiration.call()) == false);

      await tuiChainController.finalizeLoan(tuiChainLoan.address);

      return assert(false);

    } catch(e) {

      return assert(true);

    }

  });

  it("Finalize the loan", async function () {

    // 10 accounts giving 100 DAI each
    for (let index = 0; index < accounts.length; index++) {
      
      await daiMock.increaseAllowance(tuiChainLoan.address, BigInt(200) * (BigInt(10) ** BigInt(18)), {from: accounts[index]});
      await tuiChainLoan.provideFunds(BigInt(100) * (BigInt(10) ** BigInt(18)), {from: accounts[index]});  
      
    }

    // check that loan is ACTIVE 
    var events = await tuiChainLoan.getPastEvents('PhaseUpdated', {fromBlock: 0, toBlock: 'latest'});


    assert(events[0].returnValues.newPhase == Phase.Active);
    
    await tuiChainController.finalizeLoan(tuiChainLoan.address);

    events = await tuiChainLoan.getPastEvents('PhaseUpdated', {fromBlock: 0, toBlock: 'latest'});

    return assert(events[1].returnValues.newPhase == Phase.Finalized);

  });

  /* -------------------------------------------------------------------------- */

  
  it("Fail to cancel the loan if not the owner", async function () {

    const transaction = await tuiChainController.createLoan(...Object.values(loanObject));

    tuiChainLoan = await TuiChainLoan.at(transaction.logs[0].address);

    try {

      assert((await tuiChainLoan.checkExpiration.call()) == false);
    
      await tuiChainController.cancelLoan(tuiChainLoan.address, {from: accounts[1]});

    } catch(e) {

      return assert(e.message.includes('caller is not the owner'));

    }

  });

  it("Cancel loan before it expires", async function () {

    assert((await tuiChainLoan.checkExpiration.call()) == false);

    await tuiChainController.cancelLoan(tuiChainLoan.address);    

    const events = await tuiChainLoan.getPastEvents('PhaseUpdated', {fromBlock: 0, toBlock: 'latest'});

    return assert(events[0].returnValues.newPhase == Phase.Canceled);

  });

  /* -------------------------------------------------------------------------- */

  it("Fail to notify loan activation if it's not a loan", async function () {

    try {

      await tuiChainController.notifyLoanActivation();
    
    } catch(e) {

      return assert(e.message.includes('VM Exception while processing transaction: revert'));

    }

    return assert(false);

  }); 
  
  /* -------------------------------------------------------------------------- */

});
