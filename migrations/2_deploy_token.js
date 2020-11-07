const DebtToken = artifacts.require("DebtToken");

module.exports = function (deployer) {
  deployer.deploy(DebtToken, "Token", "TKN", 1000);
};
