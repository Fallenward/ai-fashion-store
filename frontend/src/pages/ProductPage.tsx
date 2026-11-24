import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ProductGrid } from "@/components/shop/ProductCard";
import { ApiError, api } from "@/lib/api";
import type { Cart, ProductCard, ProductDetail } from "@/lib/types";
import { formatMoney } from "@/lib/utils";
import { useSession } from "@/stores/session";
import { useUi } from "@/stores/ui";

export function ProductPage() {
  const { slug = "" } = useParams();
  const queryClient = useQueryClient();
  const toast = useUi((state) => state.toast);
  const openChat = useUi((state) => state.openChat);
  const { user } = useSession();
  const product = useQuery({ queryKey: ["product", slug], queryFn: () => api<ProductDetail>(`/api/products/${slug}`) });
  const related = useQuery({ queryKey: ["related", slug], queryFn: () => api<{ items: ProductCard[] }>(`/api/products/${slug}/related`) });
  const styling = useQuery({ queryKey: ["styling", slug], queryFn: () => api<{ items: ProductCard[]; explanation: string }>(`/api/products/${slug}/styling`) });
  const [color, setColor] = useState<string | null>(null);
  const [size, setSize] = useState<string | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [image, setImage] = useState(0);

  const add = useMutation({
    mutationFn: (variantId: string) => api<Cart>("/api/cart/items", { method: "POST", body: JSON.stringify({ variant_id: variantId, quantity }) }),
    onSuccess: () => {
      toast("Added to your bag");
      void queryClient.invalidateQueries({ queryKey: ["cart"] });
    },
    onError: (error) => toast(error instanceof ApiError ? error.message : "Could not add that piece", "error"),
  });
  const wish = useMutation({
    mutationFn: (productId: string) => api("/api/wishlist", { method: "POST", body: JSON.stringify({ product_id: productId }) }),
    onSuccess: () => toast("Saved to your wishlist"),
    onError: (error) => toast(error instanceof ApiError ? error.message : "Sign in to save pieces", "error"),
  });

  if (product.isLoading) return <p>Loading the piece…</p>;
  if (product.isError || !product.data) return <p>This piece is not in the shop.</p>;
  const item = product.data;
  const activeColor = color || item.colors[0];
  const activeSize = size || item.variants.find((variant) => variant.color === activeColor && variant.in_stock)?.size || item.sizes[0];
  const variant = item.variants.find((entry) => entry.color === activeColor && entry.size === activeSize);

  return (
    <div className="space-y-16">
      <div className="grid gap-10 md:grid-cols-2">
        <div>
          <div className="overflow-hidden rounded-[1.8rem] bg-white">
            <img src={item.images[image]?.url || item.image || ""} alt={item.images[image]?.alt || item.name} className="aspect-[3/4] w-full object-cover" />
          </div>
          {item.images.length > 1 && (
            <div className="mt-3 flex gap-2">
              {item.images.map((shot, index) => (
                <button key={shot.id} onClick={() => setImage(index)} className={`h-16 w-12 overflow-hidden rounded-xl border ${index === image ? "border-ink" : "border-transparent"}`}>
                  <img src={shot.url} alt="" className="h-full w-full object-cover" />
                </button>
              ))}
            </div>
          )}
        </div>
        <div>
          <p className="eyebrow">{item.brand}</p>
          <h1 className="mt-2 font-serif text-5xl">{item.name}</h1>
          <p className="mt-3 text-lg">
            {formatMoney(variant?.price || item.price)}
            {item.compare_at_price && <span className="ml-2 text-stone line-through">{formatMoney(item.compare_at_price)}</span>}
          </p>
          <p className="mt-4 max-w-lg leading-relaxed text-stone">{item.description}</p>
          <div className="mt-6">
            <p className="eyebrow">Color</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {item.colors.map((entry) => (
                <button key={entry} onClick={() => setColor(entry)} className={`rounded-full border px-4 py-2 text-sm ${entry === activeColor ? "border-ink bg-ink text-cream" : "border-line"}`}>{entry}</button>
              ))}
            </div>
          </div>
          <div className="mt-5">
            <p className="eyebrow">Size</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {item.sizes.map((entry) => {
                const match = item.variants.find((variant) => variant.size === entry && variant.color === activeColor);
                const available = !!match?.in_stock;
                return (
                  <button key={entry} disabled={!available} onClick={() => setSize(entry)} className={`h-11 min-w-11 rounded-full border px-3 text-sm disabled:opacity-30 ${entry === activeSize ? "border-ink bg-ink text-cream" : "border-line"}`}>{entry}</button>
                );
              })}
            </div>
          </div>
          <p className="mt-4 text-sm text-stone">{variant ? (variant.in_stock ? `${variant.quantity} available` : "Out of stock") : "Choose a size"}</p>
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <label className="flex h-11 items-center rounded-full border border-line px-3">
              Qty
              <input type="number" min={1} max={10} value={quantity} onChange={(event) => setQuantity(Number(event.target.value))} className="w-14 bg-transparent text-center outline-none" />
            </label>
            <button disabled={!variant?.in_stock || add.isPending} onClick={() => variant && add.mutate(variant.id)} className="h-11 rounded-full bg-ink px-6 text-sm text-cream disabled:opacity-40">
              Add to bag
            </button>
            {user ? (
              <button onClick={() => wish.mutate(item.id)} className="h-11 rounded-full border border-line px-5 text-sm">Wishlist</button>
            ) : (
              <Link to="/login" className="h-11 rounded-full border border-line px-5 py-3 text-sm">Sign in to save</Link>
            )}
          </div>
          <dl className="mt-8 space-y-2 text-sm text-stone">
            {item.material && <div><dt className="inline text-ink">Material. </dt><dd className="inline">{item.material}</dd></div>}
            {item.care && <div><dt className="inline text-ink">Care. </dt><dd className="inline">{item.care}</dd></div>}
          </dl>
        </div>
      </div>
      <section className="rounded-[1.8rem] bg-white p-6 md:p-8">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 className="font-serif text-4xl">Style it</h2>
          <button onClick={() => openChat(`How should I style the ${item.name}?`)} className="text-sm link-line">Ask the stylist about this piece</button>
        </div>
        <p className="mt-3 max-w-2xl text-stone">{styling.data?.explanation}</p>
        <div className="mt-6"><ProductGrid products={styling.data?.items || []} /></div>
      </section>
      <section>
        <h2 className="mb-6 font-serif text-4xl">Related</h2>
        <ProductGrid products={related.data?.items || []} />
      </section>
    </div>
  );
}
