import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Newsletter } from "@/components/pages/DynamicPage";
import { ProductGrid } from "@/components/shop/ProductCard";
import { api } from "@/lib/api";
import type { Category, ProductCard } from "@/lib/types";
import { useUi } from "@/stores/ui";

function useProducts(params: string) {
  return useQuery({
    queryKey: ["products", params],
    queryFn: () => api<{ items: ProductCard[] }>(`/api/products?${params}`),
  });
}

export function HomePage() {
  const openChat = useUi((state) => state.openChat);
  const categories = useQuery({ queryKey: ["categories"], queryFn: () => api<Category[]>("/api/categories") });
  const featured = useProducts("featured=true&page_size=4&sort=popularity");
  const arrivals = useProducts("is_new=true&page_size=4&sort=newest");
  const trending = useProducts("trending=true&page_size=4&sort=popularity");
  const sellers = useProducts("bestseller=true&page_size=4&sort=popularity");

  return (
    <div className="space-y-20">
      <section className="grid items-center gap-10 md:grid-cols-[1.1fr_0.9fr]">
        <div>
          <p className="eyebrow">Spring floor</p>
          <h1 className="mt-4 font-serif text-5xl leading-[0.95] md:text-7xl">Clothes with somewhere to go.</h1>
          <p className="mt-5 max-w-md text-lg text-stone">Tailoring, knits, and dresses in a quiet palette. Shop the floor, or ask the stylist to pull pieces that are actually in stock.</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/shop" className="rounded-full bg-ink px-6 py-3 text-sm text-cream">Shop the edit</Link>
            <button onClick={() => openChat("I need an outfit for a casual dinner.")} className="rounded-full border border-ink/15 px-6 py-3 text-sm">Ask the stylist</button>
          </div>
        </div>
        <Link to="/products/charcoal-wool-overcoat" className="relative block overflow-hidden rounded-[2rem] bg-ink">
          <img src="/static/products/charcoal-wool-overcoat.svg" alt="Charcoal wool overcoat" className="aspect-[4/5] w-full object-cover" />
          <span className="absolute bottom-5 left-5 text-cream">
            <span className="block text-xs uppercase tracking-[0.2em] text-cream/70">Featured</span>
            <span className="font-serif text-3xl">The charcoal coat</span>
          </span>
        </Link>
      </section>

      <section>
        <div className="mb-6 flex items-end justify-between">
          <h2 className="font-serif text-4xl">Collections</h2>
          <Link to="/shop" className="text-sm link-line">View all</Link>
        </div>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {(categories.data || []).map((category) => (
            <Link key={category.id} to={`/shop?category=${category.slug}`} className="group relative overflow-hidden rounded-[1.4rem] bg-white">
              {category.image_url && <img src={category.image_url} alt="" className="aspect-[4/5] w-full object-cover transition duration-500 group-hover:scale-105" />}
              <span className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-ink/80 to-transparent p-4 font-serif text-2xl text-cream">{category.name}</span>
            </Link>
          ))}
        </div>
      </section>

      <Section title="New arrivals" href="/shop?is_new=true" products={arrivals.data?.items} loading={arrivals.isLoading} />
      <Section title="Trending" href="/shop?trending=true" products={trending.data?.items} loading={trending.isLoading} />
      <Section title="Best sellers" href="/shop?bestseller=true" products={sellers.data?.items} loading={sellers.isLoading} />

      <section className="grid gap-6 rounded-[2rem] bg-white p-6 md:grid-cols-2 md:p-10">
        <div>
          <p className="eyebrow">This week</p>
          <h2 className="mt-2 font-serif text-4xl">Ten percent off the first order.</h2>
          <p className="mt-3 text-stone">Use WELCOME10 at checkout. Shipping is $8, and orders of $150 ship free.</p>
          <Link to="/shop" className="mt-6 inline-flex rounded-full bg-wine px-5 py-3 text-sm text-cream">Shop with the code</Link>
        </div>
        <img src="/static/products/midnight-slip-dress.svg" alt="Midnight slip dress" className="aspect-[4/3] w-full rounded-[1.4rem] object-cover" />
      </section>

      <section className="grid items-center gap-8 md:grid-cols-[0.8fr_1.2fr]">
        <div>
          <p className="eyebrow">The stylist</p>
          <h2 className="mt-2 font-serif text-4xl">Tell it the occasion. It checks the inventory.</h2>
          <p className="mt-3 text-stone">A black hoodie under $60, a dinner outfit, the return window. The answer is grounded in this shop, not a generic catalog.</p>
          <button onClick={() => openChat()} className="mt-6 rounded-full bg-ink px-5 py-3 text-sm text-cream">Open the stylist</button>
        </div>
        <Section title="From the floor" href="/shop?featured=true" products={featured.data?.items} loading={featured.isLoading} />
      </section>

      <Newsletter title="A short letter when new pieces arrive" subtitle="No daily mail. Just the floor." />
    </div>
  );
}

function Section({ title, href, products, loading }: { title: string; href: string; products?: ProductCard[]; loading: boolean }) {
  return (
    <section>
      <div className="mb-6 flex items-end justify-between">
        <h2 className="font-serif text-4xl">{title}</h2>
        <Link to={href} className="text-sm link-line">See more</Link>
      </div>
      {loading ? <p className="text-stone">Loading pieces…</p> : <ProductGrid products={products || []} />}
    </section>
  );
}
