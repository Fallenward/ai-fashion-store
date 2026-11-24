import { FormEvent, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ApiError, api } from "@/lib/api";
import type { Address, Cart } from "@/lib/types";
import { formatMoney } from "@/lib/utils";
import { useSession } from "@/stores/session";

type Quote = {
  subtotal: string;
  discount: string;
  shipping_fee: string;
  total: string;
  promo_code: string | null;
  free_shipping_remaining: string | null;
  payment_mode: "stripe" | "mock";
};

export function CheckoutPage() {
  const { user } = useSession();
  const navigate = useNavigate();
  const cart = useQuery({ queryKey: ["cart"], queryFn: () => api<Cart>("/api/cart") });
  const addresses = useQuery({ queryKey: ["addresses"], queryFn: () => api<{ items: Address[] }>("/api/account/addresses"), enabled: !!user });
  const [promo, setPromo] = useState("");
  const [quote, setQuote] = useState<Quote | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [addressId, setAddressId] = useState("");

  if (!user) return <Navigate to="/login?next=/checkout" replace />;

  async function refreshQuote(code = promo) {
    const next = await api<Quote>("/api/checkout/quote", { method: "POST", body: JSON.stringify({ promo_code: code || null }) });
    setQuote(next);
    return next;
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError("");
    const form = new FormData(event.currentTarget);
    const payload: Record<string, unknown> = {
      promo_code: promo || null,
      save_address: form.get("save_address") === "on",
    };
    if (addressId) payload.address_id = addressId;
    else {
      for (const key of ["full_name", "line1", "line2", "city", "region", "postal_code", "country"]) payload[key] = String(form.get(key) || "");
    }
    try {
      const result = await api<{ mode: string; url?: string; order_id: string }>("/api/checkout", { method: "POST", body: JSON.stringify(payload) });
      if (result.mode === "stripe" && result.url) window.location.href = result.url;
      else navigate(`/orders/${result.order_id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Checkout failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="grid gap-10 md:grid-cols-[1.2fr_0.8fr]">
      <div className="space-y-6">
        <h1 className="font-serif text-5xl">Checkout</h1>
        {addresses.data?.items.length ? (
          <label className="block text-sm">
            Saved address
            <select value={addressId} onChange={(event) => setAddressId(event.target.value)} className="mt-2 h-11 w-full rounded-2xl border border-line bg-white px-3">
              <option value="">Use a new address</option>
              {addresses.data.items.map((address) => (
                <option key={address.id} value={address.id}>{address.label}: {address.line1}, {address.city}</option>
              ))}
            </select>
          </label>
        ) : null}
        {!addressId && (
          <div className="grid gap-3 md:grid-cols-2">
            <Field name="full_name" label="Full name" defaultValue={user.full_name} />
            <Field name="line1" label="Address" className="md:col-span-2" />
            <Field name="line2" label="Apartment" required={false} />
            <Field name="city" label="City" />
            <Field name="region" label="State" />
            <Field name="postal_code" label="Postal code" />
            <Field name="country" label="Country" defaultValue="United States" />
            <label className="flex items-center gap-2 text-sm md:col-span-2">
              <input type="checkbox" name="save_address" /> Save this address
            </label>
          </div>
        )}
      </div>
      <aside className="h-fit space-y-4 rounded-[1.6rem] bg-white p-6">
        {(cart.data?.items || []).map((item) => (
          <p key={item.id} className="flex justify-between text-sm"><span>{item.product.name} × {item.quantity}</span><span>{formatMoney(item.line_total)}</span></p>
        ))}
        <div className="flex gap-2">
          <input value={promo} onChange={(event) => setPromo(event.target.value)} placeholder="Promo code" className="h-11 flex-1 rounded-full border border-line px-4" />
          <button type="button" onClick={() => refreshQuote().catch((err) => setError(err instanceof Error ? err.message : "Invalid code"))} className="h-11 rounded-full border border-ink px-4 text-sm">Apply</button>
        </div>
        {quote && (
          <div className="space-y-1 text-sm">
            <Row label="Subtotal" value={quote.subtotal} />
            <Row label="Discount" value={quote.discount} />
            <Row label="Shipping" value={quote.shipping_fee} />
            <Row label="Total" value={quote.total} />
            {quote.free_shipping_remaining && <p className="text-stone">{formatMoney(quote.free_shipping_remaining)} away from free shipping.</p>}
          </div>
        )}
        {quote?.payment_mode === "mock" || !quote ? (
          <p className="rounded-2xl bg-paper px-3 py-2 text-sm">Development mock checkout. No card is charged. This is not a real payment.</p>
        ) : (
          <p className="text-sm text-stone">You will continue to Stripe in test mode. Card details stay with Stripe.</p>
        )}
        {error && <p className="text-sm text-wine">{error}</p>}
        <button disabled={pending || !cart.data?.items.length} className="h-11 w-full rounded-full bg-ink text-sm text-cream disabled:opacity-40">
          {pending ? "Placing order…" : "Place order"}
        </button>
        <Link to="/cart" className="block text-center text-sm text-stone">Back to bag</Link>
      </aside>
    </form>
  );
}

function Field({ name, label, defaultValue, required = true, className = "" }: { name: string; label: string; defaultValue?: string; required?: boolean; className?: string }) {
  return (
    <label className={`block text-sm ${className}`}>
      {label}
      <input name={name} required={required} defaultValue={defaultValue} className="mt-1 h-11 w-full rounded-2xl border border-line bg-white px-3" />
    </label>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return <p className="flex justify-between"><span>{label}</span><span>{formatMoney(value)}</span></p>;
}
