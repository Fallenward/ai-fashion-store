import { FormEvent } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ProductGrid } from "@/components/shop/ProductCard";
import { ApiError, api, saveSession } from "@/lib/api";
import type { Address, Order, ProductCard, StyleProfile, User } from "@/lib/types";
import { formatMoney } from "@/lib/utils";
import { useSession } from "@/stores/session";
import { useUi } from "@/stores/ui";

export function AccountLayout() {
  const { user } = useSession();
  const navigate = useNavigate();
  if (!user) return <p>Please <Link to="/login" className="link-line">sign in</Link>.</p>;
  async function logout() {
    const session = JSON.parse(localStorage.getItem("atelier-auth") || "{}") as { refreshToken?: string };
    await api("/api/auth/logout", { method: "POST", body: JSON.stringify({ refresh_token: session.refreshToken }) }).catch(() => undefined);
    saveSession(null);
    navigate("/");
  }
  return (
    <div className="grid gap-8 md:grid-cols-[200px_1fr]">
      <aside className="space-y-3 text-sm">
        <p className="font-serif text-3xl">{user.full_name}</p>
        {["", "/orders", "/addresses", "/preferences"].map((path) => (
          <NavLink key={path} to={`/account${path}`} end={path === ""} className={({ isActive }) => `block ${isActive ? "text-wine" : ""}`}>
            {path === "" ? "Profile" : path.slice(1)}
          </NavLink>
        ))}
        <Link to="/wishlist" className="block">Wishlist</Link>
        <button onClick={() => void logout()} className="text-stone">Sign out</button>
      </aside>
      <Outlet />
    </div>
  );
}

export function ProfilePage() {
  const { user, setUser } = useSession();
  const toast = useUi((state) => state.toast);
  if (!user) return null;
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const next = await api<User>("/api/account/profile", { method: "PATCH", body: JSON.stringify({ full_name: form.get("full_name"), phone: form.get("phone") }) });
      setUser(next);
      toast("Profile saved");
    } catch (error) {
      toast(error instanceof ApiError ? error.message : "Could not save", "error");
    }
  }
  async function password(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await api("/api/account/password", { method: "POST", body: JSON.stringify({ current_password: form.get("current_password"), new_password: form.get("new_password") }) });
      toast("Password updated. Sign in again next time.");
      event.currentTarget.reset();
    } catch (error) {
      toast(error instanceof ApiError ? error.message : "Could not change the password", "error");
    }
  }
  return (
    <div className="space-y-8">
      <h1 className="font-serif text-4xl">Profile</h1>
      <form onSubmit={save} className="grid max-w-lg gap-3">
        <label className="text-sm">Name<input name="full_name" defaultValue={user.full_name} className="mt-1 h-11 w-full rounded-2xl border border-line px-3" /></label>
        <label className="text-sm">Phone<input name="phone" defaultValue={user.phone || ""} className="mt-1 h-11 w-full rounded-2xl border border-line px-3" /></label>
        <p className="text-sm text-stone">{user.email}</p>
        <button className="h-11 rounded-full bg-ink text-sm text-cream">Save profile</button>
      </form>
      <form onSubmit={password} className="grid max-w-lg gap-3">
        <h2 className="font-serif text-2xl">Password</h2>
        <input name="current_password" type="password" required placeholder="Current password" className="h-11 rounded-2xl border border-line px-3" />
        <input name="new_password" type="password" required minLength={8} placeholder="New password" className="h-11 rounded-2xl border border-line px-3" />
        <button className="h-11 rounded-full border border-ink text-sm">Change password</button>
      </form>
    </div>
  );
}

export function OrdersPage() {
  const orders = useQuery({ queryKey: ["orders"], queryFn: () => api<{ items: Order[] }>("/api/orders") });
  if (orders.isLoading) return <p>Loading orders…</p>;
  return (
    <div>
      <h1 className="font-serif text-4xl">Orders</h1>
      <ul className="mt-4 divide-y divide-line">
        {(orders.data?.items || []).map((order) => (
          <li key={order.id} className="flex items-center justify-between py-4">
            <div>
              <Link to={`/orders/${order.id}`} className="font-medium">{order.number}</Link>
              <p className="text-sm capitalize text-stone">{order.status}</p>
            </div>
            <span>{formatMoney(order.total)}</span>
          </li>
        ))}
        {!orders.data?.items.length && <p className="text-stone">No orders yet.</p>}
      </ul>
    </div>
  );
}

export function AddressesPage() {
  const queryClient = useQueryClient();
  const toast = useUi((state) => state.toast);
  const addresses = useQuery({ queryKey: ["addresses"], queryFn: () => api<{ items: Address[] }>("/api/account/addresses") });
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(form.entries());
    payload.is_default = form.get("is_default") === "on" ? "true" : "";
    try {
      await api("/api/account/addresses", { method: "POST", body: JSON.stringify({ ...payload, is_default: form.get("is_default") === "on" }) });
      event.currentTarget.reset();
      await queryClient.invalidateQueries({ queryKey: ["addresses"] });
    } catch (error) {
      toast(error instanceof ApiError ? error.message : "Could not save the address", "error");
    }
  }
  async function remove(id: string) {
    await api(`/api/account/addresses/${id}`, { method: "DELETE" });
    await queryClient.invalidateQueries({ queryKey: ["addresses"] });
  }
  return (
    <div className="space-y-6">
      <h1 className="font-serif text-4xl">Addresses</h1>
      <ul className="space-y-3">
        {(addresses.data?.items || []).map((address) => (
          <li key={address.id} className="flex justify-between rounded-2xl bg-white p-4 text-sm">
            <span>{address.full_name}, {address.line1}, {address.city} {address.region} {address.postal_code}{address.is_default ? " · Default" : ""}</span>
            <button onClick={() => void remove(address.id)} className="text-stone">Remove</button>
          </li>
        ))}
      </ul>
      <form onSubmit={create} className="grid max-w-lg gap-3 md:grid-cols-2">
        {["full_name", "line1", "line2", "city", "region", "postal_code", "country"].map((name) => (
          <input key={name} name={name} required={name !== "line2"} placeholder={name.replace("_", " ")} defaultValue={name === "country" ? "United States" : ""} className="h-11 rounded-2xl border border-line px-3" />
        ))}
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" name="is_default" /> Default</label>
        <button className="h-11 rounded-full bg-ink text-sm text-cream">Save address</button>
      </form>
    </div>
  );
}

export function PreferencesPage() {
  const toast = useUi((state) => state.toast);
  const queryClient = useQueryClient();
  const style = useQuery({ queryKey: ["style"], queryFn: () => api<StyleProfile>("/api/account/style") });
  const facets = useQuery({ queryKey: ["facets"], queryFn: () => api<{ sizes: string[]; colors: string[]; brands: string[] }>("/api/facets") });
  const categories = useQuery({ queryKey: ["categories"], queryFn: () => api<{ slug: string; name: string }[]>("/api/categories") });
  if (!style.data) return <p>Loading preferences…</p>;
  const current = style.data;
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const list = (name: string) => form.getAll(name).map(String);
    try {
      await api("/api/account/style", {
        method: "PUT",
        body: JSON.stringify({
          preferred_sizes: list("sizes"),
          favorite_colors: list("colors"),
          favorite_categories: list("categories"),
          preferred_brands: list("brands"),
          style_keywords: String(form.get("keywords") || "").split(",").map((item) => item.trim()).filter(Boolean),
          budget_max: form.get("budget_max") || null,
          notes: form.get("notes") || null,
        }),
      });
      await queryClient.invalidateQueries({ queryKey: ["style"] });
      toast("Preferences saved. The stylist can use them.");
    } catch (error) {
      toast(error instanceof ApiError ? error.message : "Could not save", "error");
    }
  }
  async function act(path: string) {
    await api(path, { method: path.endsWith("/style") ? "DELETE" : "POST" });
    await queryClient.invalidateQueries({ queryKey: ["style"] });
  }
  return (
    <form onSubmit={save} className="space-y-5">
      <h1 className="font-serif text-4xl">Style preferences</h1>
      {current.opted_out && <p className="rounded-2xl bg-white p-4 text-sm">Personalization is off. The stylist will not use a saved profile until you opt back in.</p>}
      <Checks name="sizes" label="Sizes" options={facets.data?.sizes || []} selected={current.preferred_sizes} />
      <Checks name="colors" label="Colors" options={facets.data?.colors || []} selected={current.favorite_colors} />
      <Checks name="categories" label="Categories" options={(categories.data || []).map((category) => category.slug)} selected={current.favorite_categories} />
      <Checks name="brands" label="Brands" options={facets.data?.brands || []} selected={current.preferred_brands} />
      <label className="block text-sm">Keywords<input name="keywords" defaultValue={current.style_keywords.join(", ")} className="mt-1 h-11 w-full rounded-2xl border border-line px-3" /></label>
      <label className="block text-sm">Budget max<input name="budget_max" defaultValue={current.budget_max || ""} className="mt-1 h-11 w-full rounded-2xl border border-line px-3" /></label>
      <label className="block text-sm">Notes<textarea name="notes" defaultValue={current.notes || ""} className="mt-1 w-full rounded-2xl border border-line p-3" rows={3} /></label>
      <div className="flex flex-wrap gap-3">
        <button className="h-11 rounded-full bg-ink px-5 text-sm text-cream">Save</button>
        <button type="button" onClick={() => void act("/api/account/style")} className="h-11 rounded-full border border-line px-5 text-sm">Clear</button>
        <button type="button" onClick={() => void act("/api/account/style/opt-out")} className="h-11 rounded-full border border-line px-5 text-sm">Opt out</button>
        <button type="button" onClick={() => void act("/api/account/style/opt-in")} className="h-11 rounded-full border border-line px-5 text-sm">Opt in</button>
      </div>
    </form>
  );
}

function Checks({ name, label, options, selected }: { name: string; label: string; options: string[]; selected: string[] }) {
  const chosen = new Set(selected.map((item) => item.toLowerCase()));
  return (
    <fieldset>
      <legend className="eyebrow">{label}</legend>
      <div className="mt-2 flex flex-wrap gap-2">
        {options.map((option) => (
          <label key={option} className="rounded-full border border-line bg-white px-3 py-1 text-sm">
            <input type="checkbox" name={name} value={option} defaultChecked={chosen.has(option.toLowerCase())} className="mr-2" />
            {option}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export function WishlistPage() {
  const { user } = useSession();
  const queryClient = useQueryClient();
  const wishlist = useQuery({ queryKey: ["wishlist"], queryFn: () => api<{ items: ProductCard[] }>("/api/wishlist"), enabled: !!user });
  if (!user) return <p>Please <Link to="/login" className="link-line">sign in</Link> to see your wishlist.</p>;
  if (wishlist.isLoading) return <p>Loading wishlist…</p>;
  async function remove(id: string) {
    await api(`/api/wishlist/${id}`, { method: "DELETE" });
    await queryClient.invalidateQueries({ queryKey: ["wishlist"] });
  }
  return (
    <div>
      <h1 className="mb-6 font-serif text-5xl">Wishlist</h1>
      <ProductGrid products={wishlist.data?.items || []} />
      <div className="mt-4 flex flex-wrap gap-3 text-sm">
        {(wishlist.data?.items || []).map((item) => (
          <button key={item.id} onClick={() => void remove(item.id)} className="text-stone">Remove {item.name}</button>
        ))}
      </div>
    </div>
  );
}
