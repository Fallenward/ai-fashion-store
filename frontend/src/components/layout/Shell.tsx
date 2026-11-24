import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { Menu, Search, ShoppingBag, UserRound, X } from "lucide-react";
import { FormEvent, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChatWidget } from "@/components/ai/ChatWidget";
import { api } from "@/lib/api";
import type { Cart } from "@/lib/types";
import { useSession } from "@/stores/session";
import { useUi } from "@/stores/ui";

const links = [
  { to: "/shop", label: "Shop" },
  { to: "/pages", label: "Journal" },
  { to: "/about", label: "About" },
];

export function StoreShell() {
  const { user } = useSession();
  const toasts = useUi((state) => state.toasts);
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const navigate = useNavigate();
  const cart = useQuery({ queryKey: ["cart", user?.id], queryFn: () => api<Cart>("/api/cart") });

  function onSearch(event: FormEvent) {
    event.preventDefault();
    navigate(search.trim() ? `/shop?q=${encodeURIComponent(search.trim())}` : "/shop");
    setOpen(false);
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-line/80 bg-paper/90 backdrop-blur">
        <div className="page flex h-16 items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <button className="md:hidden" onClick={() => setOpen((value) => !value)} aria-label="Menu">
              {open ? <X size={20} /> : <Menu size={20} />}
            </button>
            <Link to="/" className="font-serif text-2xl tracking-wide">Atelier</Link>
          </div>
          <nav className="hidden items-center gap-6 text-sm md:flex">
            {links.map((link) => (
              <NavLink key={link.to} to={link.to} className="link-line">{link.label}</NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-2">
            <form onSubmit={onSearch} className="hidden md:block">
              <label className="flex h-10 items-center gap-2 rounded-full border border-line bg-white px-3">
                <Search size={16} />
                <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search" className="w-36 bg-transparent outline-none" />
              </label>
            </form>
            <Link to={user ? "/account" : "/login"} aria-label="Account" className="grid h-10 w-10 place-items-center rounded-full hover:bg-white">
              <UserRound size={18} />
            </Link>
            <Link to="/cart" aria-label="Cart" className="relative grid h-10 w-10 place-items-center rounded-full hover:bg-white">
              <ShoppingBag size={18} />
              {!!cart.data?.item_count && <span className="absolute right-1 top-1 grid h-4 min-w-4 place-items-center rounded-full bg-wine px-1 text-[10px] text-cream">{cart.data.item_count}</span>}
            </Link>
          </div>
        </div>
        {open && (
          <div className="page space-y-3 pb-4 md:hidden">
            {links.map((link) => (
              <NavLink key={link.to} to={link.to} onClick={() => setOpen(false)} className="block py-1">{link.label}</NavLink>
            ))}
            <form onSubmit={onSearch}>
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search the shop" className="h-11 w-full rounded-full border border-line bg-white px-4" />
            </form>
          </div>
        )}
      </header>
      <main className="page py-8 md:py-12">
        <Outlet />
      </main>
      <footer className="mt-16 border-t border-line">
        <div className="page grid gap-8 py-12 md:grid-cols-4">
          <div>
            <p className="font-serif text-3xl">Atelier</p>
            <p className="mt-2 text-sm text-stone">A short list of clothes, and a stylist who checks the stock.</p>
          </div>
          {[
            ["Shop", [["/shop", "All pieces"], ["/shop?sort=newest", "New arrivals"], ["/wishlist", "Wishlist"]]],
            ["House", [["/about", "About"], ["/faq", "FAQ"], ["/contact", "Contact"]]],
            ["Care", [["/shipping", "Shipping & returns"], ["/privacy", "Privacy"], ["/terms", "Terms"]]],
          ].map(([title, items]) => (
            <div key={String(title)}>
              <p className="eyebrow">{String(title)}</p>
              <div className="mt-3 space-y-2 text-sm">
                {(items as [string, string][]).map(([href, label]) => (
                  <Link key={href} to={href} className="block link-line w-fit">{label}</Link>
                ))}
              </div>
            </div>
          ))}
        </div>
        <div className="page flex items-center justify-between border-t border-line py-4 text-xs text-stone">
          <span>© {new Date().getFullYear()} Atelier</span>
          {user?.role === "admin" && <Link to="/admin">Studio</Link>}
        </div>
      </footer>
      <ChatWidget />
      <div className="fixed bottom-5 left-5 z-40 space-y-2">
        {toasts.map((toast) => (
          <p key={toast.id} className={`rounded-full px-4 py-2 text-sm shadow-card ${toast.tone === "error" ? "bg-wine text-cream" : "bg-ink text-cream"}`}>{toast.message}</p>
        ))}
      </div>
    </div>
  );
}
