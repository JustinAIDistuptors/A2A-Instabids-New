describe("Bid card happy path", () => {
  it("uploads photo and sees preview", () => {
    cy.visit("/");
    cy.get("input[type=file]").selectFile("cypress/fixtures/roof.jpg");
    cy.contains("Next").click();
    cy.contains("Category");
    cy.contains("Looks good").click();
    cy.contains("Bid Card Preview");
  });
});