import { render, screen } from "@testing-library/react";
import { Token } from "./Token";

it("always renders a text label, not just colour (NFR-8)", () => {
  render(<Token tone="alert">Alert</Token>);
  const el = screen.getByText("Alert");
  expect(el).toBeVisible();
  expect(el.closest("[data-tone]")).toHaveAttribute("data-tone", "alert");
});
