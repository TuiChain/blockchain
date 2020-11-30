const TuiChainController = artifacts.require("TuiChainController");
const TuiChainMarket = artifacts.require("TuiChainMarket");
const TuiChainLoan = artifacts.require("TuiChainLoan");
const ERC20 = artifacts.require("ERC20");

contract("TuiChainController", function (accounts) {

  // parameters for DAI mimification
  const erc20Params = {
    name: "DAIMimification",
    symbol: "DAI",
  };

  // market fee, is equivalent to 10% of a DAI
  const marketFeeAttoDaiPerNanoDai = Math.pow(10,8);

  /* -------------------------------------------------------------------------- */

  // variable which represents the deployed controller contract
  let tuiChainController = null;

  // variable which represents the deployed market contract
  let tuiChainMarket = null;

  /* -------------------------------------------------------------------------- */

  // runs once before the first test in this block
  before( async () => {

    // contract which mimificates the DAI contract
    const daiMimification = await ERC20.new(...Object.values(erc20Params));

    tuiChainController = await TuiChainController.new(daiMimification.address, accounts[0], marketFeeAttoDaiPerNanoDai);

    // get contract from an address with at() function
    tuiChainMarket = await TuiChainMarket.at(await tuiChainController.getMarket());
  
  });

  /* -------------------------------------------------------------------------- */

  it("Change market fee to 20% and check it", async function () {

    const newFee = 2*Math.pow(10,8);
    
    await tuiChainController.setMarketFee(newFee);

    return assert((await tuiChainMarket.getFee()).toNumber() == newFee);

  });

  
  // Error: Returned error: VM Exception while processing transaction: revert
  // Something is wrong with loan creation
  it("Create a loan and check it", async function () {

    await tuiChainController.createLoan( 
      accounts[0] /* _feeRecipient */, 
      accounts[1] /* _loanRecipient */,
      120 /* _secondsToExpiration - 2 min */,
      Math.pow(10,8) /* _fundingFeeAttoDaiPerDai - 10% */,
      Math.pow(10,8) /* _paymentFeeAttoDaiPerDai - 10% */,
      Math.pow(10,9) /* _requestedValueAttoDai - 1 DAI */
    );
    
    //const loanContract = await TuiChainLoan.at(loan);

    //console.log(loan);


  });

});
