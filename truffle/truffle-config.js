/* -------------------------------------------------------------------------- */

module.exports = {

  networks: {
    ganache: {
      host: "localhost",
      port: 7545,
      network_id: "*",
    },
  },

  compilers: {
    solc: {
      version: "0.6.12",
      settings: {
        optimizer: {
          enabled: true,
          runs: 200,
        },
      },
    },
  },

};

/* -------------------------------------------------------------------------- */
