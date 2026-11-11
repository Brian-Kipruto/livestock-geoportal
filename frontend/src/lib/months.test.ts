import { monthRange } from "./months";

it("builds inclusive month ranges across years", () => {
  expect(monthRange("2025-11", "2026-02")).toEqual(["2025-11", "2025-12", "2026-01", "2026-02"]);
});
