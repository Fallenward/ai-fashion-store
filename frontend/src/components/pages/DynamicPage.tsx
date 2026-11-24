import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { ProductGrid } from "@/components/shop/ProductCard";
import { api } from "@/lib/api";
import type { PageBlock } from "@/lib/types";
import { useUi } from "@/stores/ui";

export function DynamicPage({ title, blocks }: { title?: string; blocks: PageBlock[] }) {
  return (
    <article className="space-y-16">
      {title && <h1 className="font-serif text-5xl">{title}</h1>}
      {blocks.map((block, index) => (
        <Block key={`${block.type}-${index}`} block={block} />
      ))}
    </article>
  );
}

function Block({ block }: { block: PageBlock }) {
  if (block.type === "hero") {
    return (
      <section className="grid items-end gap-8 rounded-[2rem] bg-ink px-6 py-10 text-cream md:grid-cols-2 md:px-12 md:py-16">
        <div>
          {block.eyebrow && <p className="eyebrow text-clay">{block.eyebrow}</p>}
          <h2 className="mt-3 font-serif text-5xl leading-[1.05] md:text-6xl">{block.title}</h2>
          {block.subtitle && <p className="mt-4 max-w-md text-cream/80">{block.subtitle}</p>}
          {block.cta_href && block.cta_label && (
            <Link to={block.cta_href} className="mt-6 inline-flex rounded-full bg-cream px-5 py-3 text-sm text-ink">
              {block.cta_label}
            </Link>
          )}
        </div>
        {block.image_url && <img src={block.image_url} alt="" className="aspect-[4/5] w-full rounded-[1.5rem] object-cover" />}
      </section>
    );
  }
  if (block.type === "text") {
    return (
      <section className="max-w-2xl">
        {block.heading && <h2 className="font-serif text-4xl">{block.heading}</h2>}
        <p className="mt-4 whitespace-pre-wrap text-lg leading-relaxed text-stone">{block.body}</p>
      </section>
    );
  }
  if (block.type === "image" && block.image_url) {
    return (
      <figure>
        <img src={block.image_url} alt={block.alt || ""} className="w-full rounded-[1.5rem] object-cover" />
        {block.caption && <figcaption className="mt-3 text-sm text-stone">{block.caption}</figcaption>}
      </figure>
    );
  }
  if (block.type === "product_grid" || block.type === "featured_collection") {
    return (
      <section>
        {block.title && <h2 className="mb-6 font-serif text-4xl">{block.title}</h2>}
        <ProductGrid products={block.products || []} />
      </section>
    );
  }
  if (block.type === "promo_banner") {
    const dark = block.tone !== "light";
    return (
      <section className={`rounded-[1.8rem] px-8 py-10 ${dark ? "bg-wine text-cream" : "bg-white"}`}>
        <h2 className="font-serif text-4xl">{block.title}</h2>
        {block.subtitle && <p className="mt-3 max-w-xl">{block.subtitle}</p>}
        {block.cta_href && block.cta_label && (
          <Link to={block.cta_href} className={`mt-6 inline-flex rounded-full px-5 py-3 text-sm ${dark ? "bg-cream text-ink" : "bg-ink text-cream"}`}>
            {block.cta_label}
          </Link>
        )}
      </section>
    );
  }
  if (block.type === "testimonials") {
    return (
      <section>
        <h2 className="font-serif text-4xl">{block.title}</h2>
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {(block.quotes || []).map((quote) => (
            <blockquote key={quote.quote} className="rounded-[1.4rem] bg-white p-5">
              <p className="font-serif text-2xl leading-snug">“{quote.quote}”</p>
              <footer className="mt-4 text-sm text-stone">
                {quote.author}
                {quote.detail ? ` · ${quote.detail}` : ""}
              </footer>
            </blockquote>
          ))}
        </div>
      </section>
    );
  }
  if (block.type === "faq") {
    return (
      <section className="max-w-3xl">
        <h2 className="font-serif text-4xl">{block.title}</h2>
        <div className="mt-6 divide-y divide-line">
          {(block.items || []).map((item) => (
            <details key={item.question} className="py-4">
              <summary className="cursor-pointer text-lg">{item.question}</summary>
              <p className="mt-2 whitespace-pre-wrap text-stone">{item.answer}</p>
            </details>
          ))}
        </div>
      </section>
    );
  }
  if (block.type === "newsletter") return <Newsletter title={block.title} subtitle={block.subtitle} />;
  return null;
}

export function Newsletter({ title = "Notes from the studio", subtitle }: { title?: string; subtitle?: string }) {
  const toast = useUi((state) => state.toast);
  const [email, setEmail] = useState("");
  const [pending, setPending] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    try {
      const result = await api<{ message: string }>("/api/newsletter", { method: "POST", body: JSON.stringify({ email }) });
      toast(result.message);
      setEmail("");
    } catch (error) {
      toast(error instanceof Error ? error.message : "Could not subscribe", "error");
    } finally {
      setPending(false);
    }
  }
  return (
    <section className="rounded-[1.8rem] border border-line bg-white/70 px-6 py-8 md:px-10">
      <h2 className="font-serif text-4xl">{title}</h2>
      {subtitle && <p className="mt-2 max-w-lg text-stone">{subtitle}</p>}
      <form onSubmit={submit} className="mt-5 flex flex-col gap-3 sm:flex-row">
        <input
          required
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="Email address"
          className="h-12 flex-1 rounded-full border border-line bg-cream px-5"
        />
        <button disabled={pending} className="h-12 rounded-full bg-ink px-6 text-cream">
          {pending ? "Joining…" : "Subscribe"}
        </button>
      </form>
    </section>
  );
}
