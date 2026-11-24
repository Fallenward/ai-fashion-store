import { Link } from "react-router-dom";
import type { ProductCard as Product } from "@/lib/types";
import { discountPercent, formatMoney } from "@/lib/utils";

export function ProductCard({ product }: { product: Product }) {
  const discount = discountPercent(product.price, product.compare_at_price);
  return (
    <article className="group">
      <Link to={`/products/${product.slug}`} className="block">
        <div className="relative aspect-[3/4] overflow-hidden rounded-[1.4rem] bg-white shadow-card">
          {product.image ? (
            <img src={product.image} alt={product.name} className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.03]" />
          ) : (
            <div className="flex h-full items-end bg-ink p-4 text-cream">Atelier</div>
          )}
          <div className="absolute left-3 top-3 flex gap-2">
            {product.is_new && <span className="rounded-full bg-cream/90 px-2 py-1 text-[10px] uppercase tracking-[0.16em]">New</span>}
            {discount && <span className="rounded-full bg-wine px-2 py-1 text-[10px] uppercase tracking-[0.16em] text-cream">-{discount}%</span>}
          </div>
        </div>
        <div className="mt-3 flex items-start justify-between gap-3">
          <div>
            <p className="text-[11px] uppercase tracking-[0.18em] text-stone">{product.brand}</p>
            <h3 className="font-serif text-xl leading-tight">{product.name}</h3>
          </div>
          <div className="text-right text-sm">
            <p>{formatMoney(product.price)}</p>
            {product.compare_at_price && <p className="text-stone line-through">{formatMoney(product.compare_at_price)}</p>}
          </div>
        </div>
        {!product.in_stock && <p className="mt-1 text-xs text-wine">Currently unavailable</p>}
      </Link>
    </article>
  );
}

export function ProductGrid({ products }: { products: Product[] }) {
  if (!products.length) return <p className="text-stone">Nothing matches those filters.</p>;
  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-8 md:grid-cols-3">
      {products.map((product) => (
        <ProductCard key={product.id} product={product} />
      ))}
    </div>
  );
}
