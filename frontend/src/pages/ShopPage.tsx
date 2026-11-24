import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { ProductGrid } from "@/components/shop/ProductCard";
import { api } from "@/lib/api";
import type { Category, ProductCard } from "@/lib/types";

export function ShopPage() {
  const [params, setParams] = useSearchParams();
  const categories = useQuery({ queryKey: ["categories"], queryFn: () => api<Category[]>("/api/categories") });
  const facets = useQuery({
    queryKey: ["facets"],
    queryFn: () => api<{ sizes: string[]; colors: string[]; brands: string[] }>("/api/facets"),
  });
  const query = params.toString();
  const products = useQuery({
    queryKey: ["shop", query],
    queryFn: () => api<{ items: ProductCard[]; total: number; page: number; page_size: number }>(`/api/products?${query || "page_size=12"}`),
  });

  function set(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (!value) next.delete(key);
    else next.set(key, value);
    if (key !== "page") next.delete("page");
    setParams(next);
  }

  const page = Number(products.data?.page || 1);
  const pages = Math.max(1, Math.ceil((products.data?.total || 0) / (products.data?.page_size || 12)));

  return (
    <div className="grid gap-8 md:grid-cols-[220px_1fr]">
      <aside className="space-y-5">
        <h1 className="font-serif text-4xl">Shop</h1>
        <Filter label="Category" value={params.get("category") || ""} onChange={(value) => set("category", value)} options={(categories.data || []).map((category) => ({ value: category.slug, label: category.name }))} />
        <Filter label="Size" value={params.get("size") || ""} onChange={(value) => set("size", value)} options={(facets.data?.sizes || []).map((size) => ({ value: size, label: size }))} />
        <Filter label="Color" value={params.get("color") || ""} onChange={(value) => set("color", value)} options={(facets.data?.colors || []).map((color) => ({ value: color, label: color }))} />
        <Filter label="Brand" value={params.get("brand") || ""} onChange={(value) => set("brand", value)} options={(facets.data?.brands || []).map((brand) => ({ value: brand, label: brand }))} />
        <label className="block text-sm">
          <span className="eyebrow">Sort</span>
          <select value={params.get("sort") || "newest"} onChange={(event) => set("sort", event.target.value)} className="mt-2 h-11 w-full rounded-2xl border border-line bg-white px-3">
            <option value="newest">Newest</option>
            <option value="popularity">Popularity</option>
            <option value="price_asc">Price, low to high</option>
            <option value="price_desc">Price, high to low</option>
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={params.get("in_stock") === "true"} onChange={(event) => set("in_stock", event.target.checked ? "true" : "")} />
          In stock only
        </label>
        <div className="grid grid-cols-2 gap-2">
          <input value={params.get("min_price") || ""} onChange={(event) => set("min_price", event.target.value)} placeholder="Min $" className="h-11 rounded-2xl border border-line bg-white px-3" />
          <input value={params.get("max_price") || ""} onChange={(event) => set("max_price", event.target.value)} placeholder="Max $" className="h-11 rounded-2xl border border-line bg-white px-3" />
        </div>
      </aside>
      <section>
        {params.get("q") && <p className="mb-4 text-stone">Results for “{params.get("q")}”</p>}
        {products.isLoading ? <p>Loading the floor…</p> : products.isError ? <p>The shop could not be loaded.</p> : <ProductGrid products={products.data?.items || []} />}
        <div className="mt-8 flex items-center justify-between text-sm">
          <button disabled={page <= 1} onClick={() => set("page", String(page - 1))} className="rounded-full border border-line px-4 py-2 disabled:opacity-40">Previous</button>
          <span>{page} / {pages}</span>
          <button disabled={page >= pages} onClick={() => set("page", String(page + 1))} className="rounded-full border border-line px-4 py-2 disabled:opacity-40">Next</button>
        </div>
      </section>
    </div>
  );
}

function Filter({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: { value: string; label: string }[] }) {
  return (
    <label className="block text-sm">
      <span className="eyebrow">{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} className="mt-2 h-11 w-full rounded-2xl border border-line bg-white px-3">
        <option value="">All</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>{option.label}</option>
        ))}
      </select>
    </label>
  );
}
