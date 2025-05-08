const { defineConfig } = require('cypress');

module.exports = defineConfig({
  e2e: {
    supportFile: false, // Explicitly disable the support file requirement
    setupNodeEvents(on, config) {
      // implement node event listeners here if needed
      return config;
    },
  },
});
