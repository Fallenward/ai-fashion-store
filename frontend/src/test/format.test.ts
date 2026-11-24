import { discountPercent, formatMoney } from "@/lib/utils";

describe("money", () => {
  it("formats catalog prices", () => {
    expect(formatMoney("54.00")).toBe("$54.00");
    expect(discountPercent("54.00", "68.00")).toBe(21);
    expect(discountPercent("54.00", null)).toBeNull();
  });
});
