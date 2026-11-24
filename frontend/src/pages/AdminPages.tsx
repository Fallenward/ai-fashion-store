import { FormEvent, useState } from "react";
import { Link, NavLink, Outlet, useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { DynamicPage } from "@/components/pages/DynamicPage";
import { ApiError, api } from "@/lib/api";
import type { Order, PageBlock, ProductDetail } from "@/lib/types";
import { formatMoney } from "@/lib/utils";
import { useUi } from "@/stores/ui";

const nav = [
  ["/admin", "Overview"],
  ["/admin/products", "Products"],
  ["/admin/orders", "Orders"],
  ["/admin/customers", "Customers"],
  ["/admin/pages", "Pages"],
  ["/admin/ai", "Stylist"],
  ["/admin/messages", "Inbox"],
];

export function AdminLayout() {
  return (
    <div className="grid gap-8 md:grid-cols-[180px_1fr]">
      <aside className="space-y-2 text-sm">
        <p className="font-serif text-3xl">Studio</p>
        {nav.map(([to, label]) => (
          <NavLink key={to} to={to} end={to === "/admin"} className={({ isActive }) => `block ${isActive ? "text-wine" : ""}`}>{label}</NavLink>
        ))}
        <Link to="/" className="block text-stone">Back to shop</Link>
      </aside>
      <div><Outlet /></div>
    </div>
  );
}

export function AdminHome() {
  const stats = useQuery({ queryKey: ["admin-stats"], queryFn: () => api<Stats>("/api/admin/stats") });
  if (!stats.data) return <p>Loading the studio…</p>;
  const data = stats.data;
  const max = Math.max(...data.sales_chart.map((point) => Number(point.total)), 1);
  return (
    <div className="space-y-8">
      <h1 className="font-serif text-4xl">Overview</h1>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Sales" value={formatMoney(data.total_sales)} />
        <Stat label="Orders" value={String(data.total_orders)} />
        <Stat label="Products" value={String(data.total_products)} />
        <Stat label="Customers" value={String(data.total_customers)} />
      </div>
      <section>
        <h2 className="font-serif text-2xl">Sales, last 14 days</h2>
        <div className="mt-4 flex h-40 items-end gap-1">
          {data.sales_chart.map((point) => (
            <div key={point.date} className="flex-1 rounded-t bg-ink" style={{ height: `${Math.max(4, (Number(point.total) / max) * 100)}%` }} title={`${point.date}: ${formatMoney(point.total)}`} />
          ))}
        </div>
      </section>
      <section>
        <h2 className="font-serif text-2xl">Low stock</h2>
        <ul className="mt-3 text-sm">
          {data.low_stock.map((row) => (
            <li key={row.sku}>{row.product_name} · {row.color} / {row.size} · {row.quantity} left</li>
          ))}
          {!data.low_stock.length && <li className="text-stone">Nothing is under its threshold.</li>}
        </ul>
      </section>
      <section>
        <h2 className="font-serif text-2xl">Recent orders</h2>
        {data.recent_orders.map((order) => (
          <Link key={order.id} to={`/admin/orders/${order.id}`} className="flex justify-between border-b border-line py-2 text-sm">
            <span>{order.number}</span><span className="capitalize">{order.status}</span><span>{formatMoney(order.total)}</span>
          </Link>
        ))}
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return <div className="rounded-2xl bg-white p-4"><p className="eyebrow">{label}</p><p className="mt-2 font-serif text-3xl">{value}</p></div>;
}

type Stats = {
  total_sales: string;
  total_orders: number;
  total_products: number;
  total_customers: number;
  sales_chart: { date: string; total: string }[];
  low_stock: { sku: string; product_name: string; color: string; size: string; quantity: number }[];
  recent_orders: Order[];
};

export function AdminProducts() {
  const products = useQuery({ queryKey: ["admin-products"], queryFn: () => api<AdminProduct[]>("/api/admin/products") });
  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="font-serif text-4xl">Products</h1>
        <Link to="/admin/products/new" className="rounded-full bg-ink px-4 py-2 text-sm text-cream">New product</Link>
      </div>
      <ul className="mt-4 divide-y divide-line">
        {(products.data || []).map((product) => (
          <li key={product.id} className="flex items-center justify-between py-3 text-sm">
            <Link to={`/admin/products/${product.id}`}>{product.name}</Link>
            <span>{product.category}</span>
            <span>{formatMoney(product.price)}</span>
            <span>{product.is_active ? "Live" : "Hidden"}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

type AdminProduct = { id: string; name: string; slug: string; brand: string; price: string; is_active: boolean; category: string };

export function AdminProductForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useUi((state) => state.toast);
  const existing = useQuery({ queryKey: ["admin-product", id], queryFn: () => api<ProductDetail>(`/api/admin/products/${id}`), enabled: !!id && id !== "new" });
  const categories = useQuery({ queryKey: ["admin-categories"], queryFn: () => api<{ id: string; name: string }[]>("/api/admin/categories") });
  const [variants, setVariants] = useState<{ sku: string; size: string; color: string; color_hex: string; quantity: number }[]>([
    { sku: "", size: "M", color: "Black", color_hex: "#111111", quantity: 8 },
  ]);
  const loaded = existing.data;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = {
      name: form.get("name"),
      description: form.get("description"),
      brand: form.get("brand"),
      category_id: form.get("category_id"),
      price: form.get("price"),
      compare_at_price: form.get("compare_at_price") || null,
      material: form.get("material"),
      care: form.get("care"),
      is_featured: form.get("is_featured") === "on",
      is_new: form.get("is_new") === "on",
      is_bestseller: form.get("is_bestseller") === "on",
      is_trending: form.get("is_trending") === "on",
      is_active: form.get("is_active") === "on",
      variants: (loaded ? loaded.variants.map((variant) => ({
        sku: variant.sku,
        size: variant.size,
        color: variant.color,
        color_hex: variant.color_hex,
        quantity: Number((form.get(`qty-${variant.id}`) as string) || variant.quantity),
      })) : variants),
    };
    try {
      const saved = await api<ProductDetail>(id && id !== "new" ? `/api/admin/products/${id}` : "/api/admin/products", {
        method: id && id !== "new" ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      });
      toast("Product saved");
      navigate(`/admin/products/${saved.id}`);
    } catch (error) {
      toast(error instanceof ApiError ? error.message : "Could not save the product", "error");
    }
  }

  async function upload(file: File) {
    if (!id || id === "new") return;
    const body = new FormData();
    body.append("file", file);
    await api(`/api/admin/products/${id}/images`, { method: "POST", body });
    await existing.refetch();
  }

  async function archive() {
    if (!id) return;
    await api(`/api/admin/products/${id}`, { method: "DELETE" });
    navigate("/admin/products");
  }

  if (id && id !== "new" && !loaded) return <p>Loading product…</p>;
  return (
    <form onSubmit={submit} className="max-w-2xl space-y-3">
      <h1 className="font-serif text-4xl">{loaded ? "Edit product" : "New product"}</h1>
      <input name="name" required defaultValue={loaded?.name} placeholder="Name" className="h-11 w-full rounded-2xl border border-line px-3" />
      <textarea name="description" required defaultValue={loaded?.description} placeholder="Description" className="w-full rounded-2xl border border-line p-3" rows={4} />
      <input name="brand" required defaultValue={loaded?.brand} placeholder="Brand" className="h-11 w-full rounded-2xl border border-line px-3" />
      <select name="category_id" required defaultValue={loaded?.category.id} className="h-11 w-full rounded-2xl border border-line px-3">
        <option value="">Category</option>
        {(categories.data || []).map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
      </select>
      <div className="grid grid-cols-2 gap-3">
        <input name="price" required defaultValue={loaded?.price} placeholder="Price" className="h-11 rounded-2xl border border-line px-3" />
        <input name="compare_at_price" defaultValue={loaded?.compare_at_price || ""} placeholder="Compare at" className="h-11 rounded-2xl border border-line px-3" />
        <input name="material" defaultValue={loaded?.material || ""} placeholder="Material" className="h-11 rounded-2xl border border-line px-3" />
        <input name="care" defaultValue={loaded?.care || ""} placeholder="Care" className="h-11 rounded-2xl border border-line px-3" />
      </div>
      <div className="flex flex-wrap gap-3 text-sm">
        {["is_featured", "is_new", "is_bestseller", "is_trending", "is_active"].map((flag) => (
          <label key={flag}><input type="checkbox" name={flag} defaultChecked={loaded ? Boolean(loaded[flag as keyof ProductDetail]) : flag === "is_active"} /> {flag.replace("is_", "")}</label>
        ))}
      </div>
      {loaded ? (
        <div className="space-y-2">
          {loaded.variants.map((variant) => (
            <label key={variant.id} className="flex items-center justify-between text-sm">
              <span>{variant.sku} · {variant.color} / {variant.size}</span>
              <input name={`qty-${variant.id}`} type="number" min={0} defaultValue={variant.quantity} className="h-10 w-24 rounded-full border border-line px-3" />
            </label>
          ))}
          <label className="block text-sm">Upload image
            <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => event.target.files?.[0] && void upload(event.target.files[0])} className="mt-1 block" />
          </label>
        </div>
      ) : (
        <div className="space-y-2">
          {variants.map((variant, index) => (
            <div key={index} className="grid grid-cols-5 gap-2">
              {(["sku", "size", "color", "color_hex"] as const).map((key) => (
                <input key={key} value={variant[key]} onChange={(event) => setVariants((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, [key]: event.target.value } : row))} className="h-10 rounded-xl border border-line px-2" />
              ))}
              <input type="number" value={variant.quantity} onChange={(event) => setVariants((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, quantity: Number(event.target.value) } : row))} className="h-10 rounded-xl border border-line px-2" />
            </div>
          ))}
          <button type="button" onClick={() => setVariants((rows) => [...rows, { sku: "", size: "S", color: "Black", color_hex: "#111111", quantity: 4 }])} className="text-sm">Add variant</button>
        </div>
      )}
      <div className="flex gap-3">
        <button className="h-11 rounded-full bg-ink px-5 text-sm text-cream">Save</button>
        {loaded && <button type="button" onClick={() => void archive()} className="h-11 rounded-full border border-line px-5 text-sm">Hide from shop</button>}
      </div>
    </form>
  );
}

export function AdminOrders() {
  const orders = useQuery({ queryKey: ["admin-orders"], queryFn: () => api<{ items: Order[] }>("/api/admin/orders") });
  return (
    <div>
      <h1 className="font-serif text-4xl">Orders</h1>
      <ul className="mt-4 divide-y divide-line">
        {(orders.data?.items || []).map((order) => (
          <li key={order.id}>
            <Link to={`/admin/orders/${order.id}`} className="flex justify-between py-3 text-sm">
              <span>{order.number}</span><span className="capitalize">{order.status}</span><span>{formatMoney(order.total)}</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function AdminOrderDetail() {
  const { id = "" } = useParams();
  const queryClient = useQueryClient();
  const order = useQuery({ queryKey: ["admin-order", id], queryFn: () => api<Order>(`/api/admin/orders/${id}`) });
  if (!order.data) return <p>Loading order…</p>;
  async function setStatus(status: string) {
    await api(`/api/admin/orders/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
    await queryClient.invalidateQueries({ queryKey: ["admin-order", id] });
  }
  return (
    <div className="space-y-4">
      <h1 className="font-serif text-4xl">{order.data.number}</h1>
      <p className="capitalize">{order.data.status} · {order.data.email}</p>
      <ul className="text-sm">
        {order.data.items.map((item) => <li key={item.id}>{item.product_name} · {item.size}/{item.color} × {item.quantity}</li>)}
      </ul>
      <p>Total {formatMoney(order.data.total)} · Payment {order.data.payment?.provider} / {order.data.payment?.status}</p>
      <div className="flex flex-wrap gap-2">
        {["processing", "shipped", "delivered", "cancelled", "refunded"].map((status) => (
          <button key={status} onClick={() => void setStatus(status)} className="rounded-full border border-line px-3 py-2 text-sm capitalize">{status}</button>
        ))}
        <button onClick={() => void api(`/api/admin/orders/${id}/refund`, { method: "POST" }).then(() => queryClient.invalidateQueries({ queryKey: ["admin-order", id] }))} className="rounded-full bg-wine px-3 py-2 text-sm text-cream">Refund</button>
      </div>
    </div>
  );
}

export function AdminCustomers() {
  const customers = useQuery({ queryKey: ["admin-customers"], queryFn: () => api<{ id: string; full_name: string; email: string }[]>("/api/admin/customers") });
  return (
    <div>
      <h1 className="font-serif text-4xl">Customers</h1>
      <ul className="mt-4 divide-y divide-line">
        {(customers.data || []).map((customer) => (
          <li key={customer.id}><Link to={`/admin/customers/${customer.id}`} className="flex justify-between py-3 text-sm"><span>{customer.full_name}</span><span>{customer.email}</span></Link></li>
        ))}
      </ul>
    </div>
  );
}

export function AdminCustomer() {
  const { id = "" } = useParams();
  const customer = useQuery({ queryKey: ["admin-customer", id], queryFn: () => api<CustomerDetail>(`/api/admin/customers/${id}`) });
  if (!customer.data) return <p>Loading customer…</p>;
  const data = customer.data;
  return (
    <div className="space-y-4">
      <h1 className="font-serif text-4xl">{data.user.full_name}</h1>
      <p className="text-sm text-stone">{data.user.email}</p>
      <p className="text-sm">Style opt-out: {data.style?.opted_out ? "yes" : "no"}</p>
      <ul className="text-sm">{data.orders.map((order) => <li key={order.id}>{order.number} · {order.status} · {formatMoney(order.total)}</li>)}</ul>
    </div>
  );
}

type CustomerDetail = { user: { full_name: string; email: string }; style: { opted_out: boolean } | null; orders: Order[] };

export function AdminPages() {
  const pages = useQuery({ queryKey: ["admin-pages"], queryFn: () => api<AdminPage[]>("/api/admin/pages") });
  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="font-serif text-4xl">Pages</h1>
        <Link to="/admin/pages/new" className="rounded-full bg-ink px-4 py-2 text-sm text-cream">New page</Link>
      </div>
      <ul className="mt-4 divide-y divide-line">
        {(pages.data || []).map((page) => (
          <li key={page.id} className="flex justify-between py-3 text-sm">
            <Link to={`/admin/pages/${page.id}`}>{page.title}</Link>
            <span className="capitalize">{page.status}{page.has_unpublished_changes ? " · draft changes" : ""}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

type AdminPage = { id: string; title: string; slug: string; status: string; has_unpublished_changes: boolean };

export function AdminPageEditor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useUi((state) => state.toast);
  const page = useQuery({
    queryKey: ["admin-page", id],
    queryFn: () => api<PageDetail>(`/api/admin/pages/${id}`),
    enabled: !!id && id !== "new",
  });
  const products = useQuery({ queryKey: ["admin-products"], queryFn: () => api<AdminProduct[]>("/api/admin/products") });
  const [blocks, setBlocks] = useState<PageBlock[] | null>(null);
  const currentBlocks = blocks || (page.data?.draft_definition.blocks as PageBlock[] | undefined) || [{ type: "hero", title: "New page", subtitle: "" }];

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const definition = { blocks: currentBlocks };
    try {
      const saved = await api<PageDetail>(id && id !== "new" ? `/api/admin/pages/${id}` : "/api/admin/pages", {
        method: id && id !== "new" ? "PATCH" : "POST",
        body: JSON.stringify({ title: form.get("title"), summary: form.get("summary"), slug: form.get("slug") || null, definition }),
      });
      toast("Draft saved");
      navigate(`/admin/pages/${saved.id}`);
    } catch (error) {
      toast(error instanceof ApiError ? error.message : "Could not save the page", "error");
    }
  }

  async function publish(confirm: boolean) {
    if (!id || id === "new") return;
    await api(`/api/admin/pages/${id}/${confirm ? "publish" : "unpublish"}`, { method: "POST", body: JSON.stringify({ confirm: true }) });
    await page.refetch();
    toast(confirm ? "Published" : "Unpublished");
  }

  function updateBlock(index: number, patch: Partial<PageBlock> & { product_ids?: string[] }) {
    setBlocks(currentBlocks.map((block, blockIndex) => blockIndex === index ? { ...block, ...patch } : block));
  }

  return (
    <div className="grid gap-8 lg:grid-cols-2">
      <form onSubmit={save} className="space-y-3">
        <h1 className="font-serif text-4xl">Page draft</h1>
        <input name="title" required defaultValue={page.data?.title} placeholder="Title" className="h-11 w-full rounded-2xl border border-line px-3" />
        <input name="slug" defaultValue={page.data?.slug} placeholder="Address" className="h-11 w-full rounded-2xl border border-line px-3" />
        <input name="summary" defaultValue={page.data?.summary || ""} placeholder="Summary" className="h-11 w-full rounded-2xl border border-line px-3" />
        {currentBlocks.map((block, index) => (
          <div key={index} className="space-y-2 rounded-2xl border border-line p-3">
            <select value={block.type} onChange={(event) => updateBlock(index, { type: event.target.value })} className="h-10 rounded-xl border border-line px-2">
              {["hero", "text", "product_grid", "promo_banner", "newsletter", "faq"].map((type) => <option key={type}>{type}</option>)}
            </select>
            <input value={block.title || block.heading || ""} onChange={(event) => updateBlock(index, block.type === "text" ? { heading: event.target.value } : { title: event.target.value })} placeholder="Heading" className="h-10 w-full rounded-xl border border-line px-2" />
            <textarea value={block.subtitle || block.body || ""} onChange={(event) => updateBlock(index, block.type === "text" ? { body: event.target.value } : { subtitle: event.target.value })} placeholder="Text" className="w-full rounded-xl border border-line p-2" rows={3} />
            {block.type === "product_grid" && (
              <select multiple value={(block as PageBlock & { product_ids?: string[] }).product_ids || []} onChange={(event) => updateBlock(index, { product_ids: Array.from(event.target.selectedOptions).map((option) => option.value) })} className="h-28 w-full rounded-xl border border-line">
                {(products.data || []).map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}
              </select>
            )}
            <button type="button" onClick={() => setBlocks(currentBlocks.filter((_, blockIndex) => blockIndex !== index))} className="text-xs text-stone">Remove block</button>
          </div>
        ))}
        <button type="button" onClick={() => setBlocks([...currentBlocks, { type: "text", heading: "Section", body: "" }])} className="text-sm">Add block</button>
        <div className="flex flex-wrap gap-2">
          <button className="h-11 rounded-full bg-ink px-5 text-sm text-cream">Save draft</button>
          {id && id !== "new" && <button type="button" onClick={() => void publish(true)} className="h-11 rounded-full bg-wine px-5 text-sm text-cream">Publish</button>}
          {id && id !== "new" && <button type="button" onClick={() => void publish(false)} className="h-11 rounded-full border border-line px-5 text-sm">Unpublish</button>}
        </div>
      </form>
      <div>
        <p className="eyebrow">Preview</p>
        <div className="mt-3 rounded-[1.4rem] bg-paper p-4">
          <DynamicPage blocks={page.data?.resolved_draft.blocks || currentBlocks} />
        </div>
      </div>
    </div>
  );
}

type PageDetail = {
  id: string;
  title: string;
  slug: string;
  summary: string | null;
  status: string;
  draft_definition: { blocks: PageBlock[] };
  resolved_draft: { blocks: PageBlock[] };
};

export function AdminAI() {
  const toast = useUi((state) => state.toast);
  const settings = useQuery({ queryKey: ["ai-settings"], queryFn: () => api<AISettings>("/api/admin/ai/settings") });
  const actions = useQuery({ queryKey: ["ai-actions"], queryFn: () => api<AIAction[]>("/api/admin/ai/actions") });
  const conversations = useQuery({ queryKey: ["ai-conversations"], queryFn: () => api<AIConversation[]>("/api/admin/ai/conversations") });
  const knowledge = useQuery({ queryKey: ["ai-knowledge"], queryFn: () => api<{ id: string; title: string; source_type: string; is_active: boolean }[]>("/api/admin/ai/knowledge") });
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const next = await api("/api/admin/ai/settings", {
      method: "PUT",
      body: JSON.stringify({
        provider: form.get("provider"),
        gemini_model: form.get("gemini_model"),
        ollama_base_url: form.get("ollama_base_url"),
        ollama_model: form.get("ollama_model"),
        embedding_provider: form.get("embedding_provider"),
      }),
    });
    toast("Provider settings saved. API keys stay in the environment.");
    return next;
  }
  async function run(path: string) {
    try {
      const result = await api<Record<string, number>>(path, { method: "POST" });
      toast(`Done: ${JSON.stringify(result)}`);
      await knowledge.refetch();
    } catch (error) {
      toast(error instanceof ApiError ? error.message : "Ingestion failed", "error");
    }
  }
  if (!settings.data) return <p>Loading stylist settings…</p>;
  return (
    <div className="space-y-8">
      <h1 className="font-serif text-4xl">Stylist</h1>
      <p className="text-sm text-stone">Gemini key present: {settings.data.gemini_key_present ? "yes" : "no"}. Payments: {settings.data.payments}.</p>
      <form onSubmit={(event) => void save(event)} className="grid max-w-xl gap-3">
        <select name="provider" defaultValue={settings.data.provider} className="h-11 rounded-2xl border border-line px-3">
          <option value="gemini">gemini</option>
          <option value="ollama">ollama</option>
          <option value="none">none</option>
        </select>
        <input name="gemini_model" defaultValue={settings.data.gemini_model} className="h-11 rounded-2xl border border-line px-3" />
        <input name="ollama_base_url" defaultValue={settings.data.ollama_base_url} className="h-11 rounded-2xl border border-line px-3" />
        <input name="ollama_model" defaultValue={settings.data.ollama_model} placeholder="Ollama model" className="h-11 rounded-2xl border border-line px-3" />
        <select name="embedding_provider" defaultValue={settings.data.embedding_provider} className="h-11 rounded-2xl border border-line px-3">
          <option value="local">local</option>
          <option value="gemini">gemini</option>
          <option value="ollama">ollama</option>
        </select>
        <button className="h-11 rounded-full bg-ink text-sm text-cream">Save provider</button>
      </form>
      <div className="flex flex-wrap gap-2">
        <button onClick={() => void run("/api/admin/ai/ingest/products")} className="rounded-full border border-line px-4 py-2 text-sm">Ingest products</button>
        <button onClick={() => void run("/api/admin/ai/ingest/documents")} className="rounded-full border border-line px-4 py-2 text-sm">Ingest policies</button>
        <button onClick={() => void run("/api/admin/ai/reindex")} className="rounded-full border border-line px-4 py-2 text-sm">Rebuild vectors</button>
      </div>
      <section>
        <h2 className="font-serif text-2xl">Knowledge</h2>
        <ul className="mt-2 text-sm">{(knowledge.data || []).map((doc) => <li key={doc.id}>{doc.source_type}: {doc.title}{doc.is_active ? "" : " (inactive)"}</li>)}</ul>
      </section>
      <section>
        <h2 className="font-serif text-2xl">Conversations</h2>
        <ul className="mt-2 text-sm">{(conversations.data || []).map((item) => <li key={item.id}>{item.title} · {item.role_context}</li>)}</ul>
      </section>
      <section>
        <h2 className="font-serif text-2xl">Actions</h2>
        <ul className="mt-2 space-y-1 text-sm">{(actions.data || []).slice(0, 30).map((action) => <li key={action.id}>{action.tool_name} · {action.status}{action.error ? ` · ${action.error}` : ""}</li>)}</ul>
      </section>
    </div>
  );
}

type AISettings = { provider: string; gemini_model: string; ollama_base_url: string; ollama_model: string; embedding_provider: string; gemini_key_present: boolean; payments: string };
type AIAction = { id: string; tool_name: string; status: string; error: string | null };
type AIConversation = { id: string; title: string; role_context: string };

export function AdminInbox() {
  const messages = useQuery({ queryKey: ["messages"], queryFn: () => api<{ id: string; name: string; email: string; subject: string; message: string }[]>("/api/admin/messages") });
  return (
    <div>
      <h1 className="font-serif text-4xl">Inbox</h1>
      <ul className="mt-4 space-y-4">
        {(messages.data || []).map((message) => (
          <li key={message.id} className="rounded-2xl bg-white p-4">
            <p className="font-medium">{message.subject}</p>
            <p className="text-sm text-stone">{message.name} · {message.email}</p>
            <p className="mt-2 whitespace-pre-wrap text-sm">{message.message}</p>
          </li>
        ))}
        {!messages.data?.length && <p className="text-stone">No messages yet.</p>}
      </ul>
    </div>
  );
}
