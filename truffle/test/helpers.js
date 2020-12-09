const BN = require('bn.js');

module.exports.fundsToInt = function (funds) {
  return funds.div(new BN('1000000000000000000')).toNumber();
}
