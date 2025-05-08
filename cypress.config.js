const { defineConfig } = require('cypress')

module.exports = defineConfig({
  e2e: {
    baseUrl: 'http://localhost:3000',
    setupNodeEvents(on, config) {
      // implement node event listeners here
    },
    // Set up timeouts for tests
    defaultCommandTimeout: 10000,
    responseTimeout: 30000,
    requestTimeout: 30000,
    viewportWidth: 1280,
    viewportHeight: 720,
  },
  env: {
    // Environment variables for Cypress tests
    SUPABASE_URL: process.env.SUPABASE_URL || 'http://localhost:5432',
    SUPABASE_ANON_KEY: process.env.SUPABASE_ANON_KEY || 'dummy',
    MOCK_SERVICES: process.env.MOCK_SERVICES || 'true',
  },
  // Configure where Cypress stores screenshots and videos
  screenshotsFolder: 'cypress/screenshots',
  videosFolder: 'cypress/videos',
  // Disable video recording in CI to speed up tests
  video: false,
  // Configure retries for flaky tests
  retries: {
    runMode: 2,
    openMode: 0,
  },
})
