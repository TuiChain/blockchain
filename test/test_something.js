/* -------------------------------------------------------------------------- */

const DaiMock = artifacts.require("DaiMock");
const TuiChainToken = artifacts.require("TuiChainToken");

/* -------------------------------------------------------------------------- */

contract("A sequence of tests", function(accounts) {

  // accounts is a list of addresses (strings). By default, contract creation
  // and calls are from the first address.

  before(async function() {
    this.dai = await DaiMock.new();
  });

  it("The first test of the sequence of tests", async function() {
    console.log(
      await this.dai.balanceOf("0x0000000000000000000000000000000000000000")
      );
  });

  it("And now the second and last test", async function() {
  });

  // const debtTokenInitialParams = {
  //   name: "Test Token",
  //   symbol: "TT",
  //   supply: 1000000
  // }

  // let debtToken = null;

  // before(async () => {
  //   debtToken = await TuiChainToken.new(...Object.values(debtTokenInitialParams));
  // });

  // it("Should deploy DebToken smart contract properly", async () => {
  //   return assert.isTrue(debtToken.address !== '');
  // });

  // it("Should have the correct name", async () => {
  //   const name = await debtToken.name();
  //   return assert(name === "Test Token");
  // });

  // it("Should have the correct symbol", async () => {
  //   const symbol = await debtToken.symbol();
  //   return assert(symbol === "TT");
  // });

  // it("Should have the correct total supply", async () => {
  //   const supply = await debtToken.totalSupply();
  //   return assert(supply.toNumber() === 1000000);
  // });

  // it("Owner should have the total supply", async () => {
  //   const balance = await debtToken.balanceOf(accounts[0]);
  //   return assert(balance.toNumber() === 1000000);
  // });

  // it("Should transfer manually tokens", async () => {
  //   await debtToken.manualTransfer(accounts[0], accounts[1], 1000);
  //   const balance0 = await debtToken.balanceOf(accounts[0]);
  //   const balance1 = await debtToken.balanceOf(accounts[1]);
  //   assert(balance0.toNumber() === 999000);
  //   assert(balance1.toNumber() === 1000);
  // });

  // it("Should not transfer tokens when the user has not enough balance", async () => {
  //   try {
  //     await debtToken.manualTransfer(accounts[1], accounts[2], 1001);
  //   } catch(exception) {
  //     const balance1 = await debtToken.balanceOf(accounts[1]);
  //     const balance2 = await debtToken.balanceOf(accounts[2]);
  //     assert(balance1.toNumber() === 1000);
  //     assert(balance2.toNumber() === 0);
  //     return;
  //   }
  //   assert(false);
  // });

});

/* -------------------------------------------------------------------------- */
