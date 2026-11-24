import { FormEvent, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { DynamicPage } from "@/components/pages/DynamicPage";
import { ApiError, api } from "@/lib/api";
import type { PageBlock } from "@/lib/types";
import { useUi } from "@/stores/ui";

export function CmsPage({ slug }: { slug?: string }) {
  const params = useParams();
  const key = slug || params.slug || "";
  const page = useQuery({
    queryKey: ["page", key],
    queryFn: () => api<{ title: string; definition: { blocks: PageBlock[] } }>(`/api/pages/${key}`),
    enabled: !!key,
  });
  if (page.isLoading) return <p>Loading…</p>;
  if (page.isError || !page.data) return <p>This page is not published.</p>;
  return <DynamicPage title={page.data.title} blocks={page.data.definition.blocks} />;
}

export function JournalPage() {
  const pages = useQuery({ queryKey: ["pages"], queryFn: () => api<{ title: string; slug: string; summary: string | null }[]>("/api/pages") });
  return (
    <div>
      <h1 className="font-serif text-5xl">Journal</h1>
      <div className="mt-6 grid gap-4 md:grid-cols-2">
        {(pages.data || []).map((page) => (
          <Link key={page.slug} to={fixedPath(page.slug)} className="rounded-[1.4rem] bg-white p-6">
            <h2 className="font-serif text-3xl">{page.title}</h2>
            {page.summary && <p className="mt-2 text-stone">{page.summary}</p>}
          </Link>
        ))}
      </div>
    </div>
  );
}

function fixedPath(slug: string) {
  const known: Record<string, string> = { about: "/about", faq: "/faq", privacy: "/privacy", terms: "/terms", "shipping-returns": "/shipping" };
  return known[slug] || `/pages/${slug}`;
}

export function ContactPage() {
  const toast = useUi((state) => state.toast);
  const [pending, setPending] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setPending(true);
    try {
      const result = await api<{ message: string }>("/api/contact", {
        method: "POST",
        body: JSON.stringify({ name: form.get("name"), email: form.get("email"), subject: form.get("subject"), message: form.get("message") }),
      });
      toast(result.message);
      event.currentTarget.reset();
    } catch (error) {
      toast(error instanceof ApiError ? error.message : "Could not send the message", "error");
    } finally {
      setPending(false);
    }
  }
  return (
    <form onSubmit={submit} className="mx-auto max-w-xl space-y-3">
      <h1 className="font-serif text-5xl">Contact</h1>
      <p className="text-stone">Questions about an order or a return land in the studio inbox.</p>
      <input name="name" required placeholder="Name" className="h-11 w-full rounded-2xl border border-line px-3" />
      <input name="email" type="email" required placeholder="Email" className="h-11 w-full rounded-2xl border border-line px-3" />
      <input name="subject" required placeholder="Subject" className="h-11 w-full rounded-2xl border border-line px-3" />
      <textarea name="message" required minLength={5} rows={5} placeholder="Message" className="w-full rounded-2xl border border-line p-3" />
      <button disabled={pending} className="h-11 rounded-full bg-ink px-6 text-sm text-cream">Send</button>
    </form>
  );
}
