import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ApiError, api } from "@/lib/api";
import type { Cart } from "@/lib/types";
import { formatMoney } from "@/lib/utils";
import { useUi } from "@/stores/ui";

export function CartPage() {
  const queryClient = useQueryClient();
  const toast = useUi((state) => state.toast);
  const cart = useQuery({ queryKey: ["cart"], queryFn: () => api<Cart>("/api/cart") });
  const update = useMutation({
    mutationFn: ({ id, quantity }: { id: string; quantity: number }) => api<Cart>(`/api/cart/items/${id}`, { method: "PATCH", body: JSON.stringify({ quantity }) }),
    onSuccess: (data) => queryClient.setQueryData(["cart"], data),
    onError: (error) => toast(error instanceof ApiError ? error.message : "Could not update the bag", "error"),
  });
  const remove = useMutation({
    mutationFn: (id: string) => api<Cart>(`/api/cart/items/${id}`, { method: "DELETE" }),
    onSuccess: (data) => queryClient.setQueryData(["cart"], data),
  });

  if (cart.isLoading) return <p>Loading your bag…</p>;
  const data = cart.data;
  if (!data?.items.length) {
    return (
      <div>
        <h1 className="font-serif text-5xl">Your bag is empty</h1>
        <Link to="/shop" className="mt-6 inline-flex rounded-full bg-ink px-5 py-3 text-sm text-cream">Browse the shop</Link>
      </div>
    );
  }
  return (
    <div className="grid gap-10 md:grid-cols-[1.4fr_0.6fr]">
      <div>
        <h1 className="font-serif text-5xl">Bag</h1>
        <ul className="mt-6 divide-y divide-line">
          {data.items.map((item) => (
            <li key={item.id} className="flex gap-4 py-5">
              {item.product.image && <img src={item.product.image} alt="" className="h-28 w-20 rounded-2xl object-cover" />}
              <div className="flex-1">
                <Link to={item.product.url} className="font-serif text-2xl">{item.product.name}</Link>
                <p className="text-sm text-stone">{item.variant.color} / {item.variant.size}</p>
                {!item.purchasable && <p className="text-sm text-wine">This option is no longer available at that quantity.</p>}
                <div className="mt-3 flex items-center gap-3">
                  <input type="number" min={1} max={10} value={item.quantity} onChange={(event) => update.mutate({ id: item.id, quantity: Number(event.target.value) })} className="h-10 w-16 rounded-full border border-line bg-white text-center" />
                  <button onClick={() => remove.mutate(item.id)} className="text-sm text-stone">Remove</button>
                </div>
              </div>
              <p>{formatMoney(item.line_total)}</p>
            </li>
          ))}
        </ul>
      </div>
      <aside className="h-fit rounded-[1.6rem] bg-white p-6">
        <p className="flex justify-between"><span>Subtotal</span><span>{formatMoney(data.subtotal)}</span></p>
        <p className="mt-2 text-sm text-stone">Shipping and any code are calculated at checkout.</p>
        <Link to="/checkout" className="mt-5 flex h-11 items-center justify-center rounded-full bg-ink text-sm text-cream">Checkout</Link>
      </aside>
    </div>
  );
}
