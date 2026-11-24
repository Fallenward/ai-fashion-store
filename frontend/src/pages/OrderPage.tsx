import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "@/lib/api";
import type { Order } from "@/lib/types";
import { formatMoney } from "@/lib/utils";

export function OrderPage() {
  const { id = "" } = useParams();
  const queryClient = useQueryClient();
  const order = useQuery({
    queryKey: ["order", id],
    queryFn: () => api<Order>(`/api/orders/${id}`),
    refetchInterval: (query) => (query.state.data?.status === "pending" && query.state.data.payment?.provider === "stripe" ? 2000 : false),
  });

  async function mockPay() {
    await api(`/api/checkout/${id}/mock-pay`, { method: "POST" });
    await queryClient.invalidateQueries({ queryKey: ["order", id] });
  }

  if (order.isLoading) return <p>Loading the order…</p>;
  if (order.isError || !order.data) return <p>That order could not be found.</p>;
  const data = order.data;
  const mockPending = data.status === "pending" && data.payment?.provider === "mock";
  return (
    <div className="mx-auto max-w-2xl">
      <p className="eyebrow">Order {data.number}</p>
      <h1 className="mt-2 font-serif text-5xl capitalize">{data.status}</h1>
      {mockPending && (
        <div className="mt-6 rounded-[1.4rem] border border-wine/30 bg-white p-5">
          <p className="font-medium">Development mock payment</p>
          <p className="mt-1 text-sm text-stone">No card is charged. Confirming marks the order paid and updates inventory so you can try the rest of the shop.</p>
          <button onClick={() => void mockPay()} className="mt-4 rounded-full bg-ink px-5 py-3 text-sm text-cream">Complete mock payment</button>
        </div>
      )}
      {data.status === "pending" && data.payment?.provider === "stripe" && <p className="mt-4 text-stone">Waiting for Stripe to confirm the payment. This page checks the order on the server.</p>}
      <ul className="mt-8 divide-y divide-line">
        {data.items.map((item) => (
          <li key={item.id} className="flex justify-between py-3 text-sm">
            <span>{item.product_name} · {item.color} / {item.size} × {item.quantity}</span>
            <span>{formatMoney(item.unit_price)}</span>
          </li>
        ))}
      </ul>
      <p className="mt-4 flex justify-between"><span>Total</span><span>{formatMoney(data.total)}</span></p>
      <p className="mt-2 text-sm text-stone">Shipping {formatMoney(data.shipping_fee)} · Discount {formatMoney(data.discount)}</p>
      <Link to="/account/orders" className="mt-6 inline-block text-sm link-line">All orders</Link>
    </div>
  );
}
