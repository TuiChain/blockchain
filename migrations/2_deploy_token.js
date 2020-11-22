const DebtToken = artifacts.require("DebtToken");
const Crowdsale = artifacts.require("Crowdsale");

var tokenName = "Token";
var tokenSymbol = "TKN";
var initialSupply = 1000;

module.exports = function (deployer) {
  deployer.deploy(DebtToken, tokenName, tokenSymbol, initialSupply);
    //.then(() => {
      //deployer.deploy(Crowdsale, Date.now(), Date.now() + (1000*60*60*24*10), 1/(3*(10^15)) , DebtToken.address)
    //});
};
