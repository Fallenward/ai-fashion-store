import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ProductCard } from "@/components/shop/ProductCard";
import type { ProductCard as Product } from "@/lib/types";

const product: Product = {
  id: "1",
  slug: "black-oversized-hoodie",
  name: "Black Oversized Hoodie",
  brand: "Halden",
  price: "54.00",
  compare_at_price: "68.00",
  currency: "USD",
  category: { id: "c", slug: "tops", name: "Tops" },
  image: "/static/products/black-oversized-hoodie.svg",
  colors: ["Black"],
  sizes: ["M"],
  in_stock: true,
  is_new: false,
  is_bestseller: true,
  is_featured: true,
  is_trending: true,
  url: "/products/black-oversized-hoodie",
};

describe("ProductCard", () => {
  it("links the real product and price", () => {
    render(
      <MemoryRouter>
        <ProductCard product={product} />
      </MemoryRouter>,
    );
    expect(screen.getByRole("link")).toHaveAttribute("href", "/products/black-oversized-hoodie");
    expect(screen.getByText("Black Oversized Hoodie")).toBeInTheDocument();
    expect(screen.getByText("$54.00")).toBeInTheDocument();
  });
});
