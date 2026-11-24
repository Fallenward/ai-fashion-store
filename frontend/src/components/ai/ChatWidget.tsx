import { FormEvent, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { MessageCircle, X } from "lucide-react";
import { api } from "@/lib/api";
import type { ChatResponse, ProductCard } from "@/lib/types";
import { formatMoney } from "@/lib/utils";
import { useUi } from "@/stores/ui";

type Message = { role: "user" | "assistant"; content: string; products?: ProductCard[]; page?: ChatResponse["page"] };

const STORAGE = "atelier-conversation";

export function ChatWidget() {
  const open = useUi((state) => state.chatOpen);
  const draft = useUi((state) => state.chatDraft);
  const openChat = useUi((state) => state.openChat);
  const closeChat = useUi((state) => state.closeChat);
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState("");
  const [pending, setPending] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([
    "I'm looking for a black oversized hoodie under $60.",
    "I need an outfit for a casual dinner.",
    "What is your return policy?",
  ]);
  const [conversationId, setConversationId] = useState<string | null>(() => localStorage.getItem(STORAGE));
  const scroller = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (draft) setText(draft);
  }, [draft]);

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight });
  }, [messages, pending, open]);

  useEffect(() => {
    if (!conversationId || messages.length) return;
    api<{ messages: Message[] }>(`/api/ai/conversations/${conversationId}`)
      .then((data) => setMessages(data.messages))
      .catch(() => {
        localStorage.removeItem(STORAGE);
        setConversationId(null);
      });
  }, [conversationId, messages.length]);

  async function send(message: string) {
    const trimmed = message.trim();
    if (!trimmed || pending) return;
    setMessages((current) => [...current, { role: "user", content: trimmed }]);
    setText("");
    setPending(true);
    try {
      const result = await api<ChatResponse>("/api/ai/chat", {
        method: "POST",
        body: JSON.stringify({ message: trimmed, conversation_id: conversationId }),
      });
      localStorage.setItem(STORAGE, result.conversation_id);
      setConversationId(result.conversation_id);
      setSuggestions(result.suggestions);
      setMessages((current) => [...current, { role: "assistant", content: result.reply, products: result.products, page: result.page }]);
    } catch (error) {
      setMessages((current) => [...current, { role: "assistant", content: error instanceof Error ? error.message : "The stylist is unavailable." }]);
    } finally {
      setPending(false);
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void send(text);
  }

  return (
    <>
      {!open && (
        <button onClick={() => openChat()} className="fixed bottom-5 right-5 z-40 flex items-center gap-2 rounded-full bg-ink px-4 py-3 text-sm text-cream shadow-card" aria-label="Open the stylist">
          <MessageCircle size={18} />
          Ask the stylist
        </button>
      )}
      {open && (
        <section className="fixed inset-x-3 bottom-3 z-40 flex h-[min(720px,calc(100vh-1.5rem))] flex-col overflow-hidden rounded-[1.6rem] border border-line bg-cream shadow-card md:inset-x-auto md:right-5 md:w-[400px]" aria-label="Shopping stylist">
          <header className="flex items-center justify-between border-b border-line px-4 py-3">
            <div>
              <p className="eyebrow">Atelier</p>
              <h2 className="font-serif text-2xl">Stylist</h2>
            </div>
            <div className="flex gap-2">
              <button
                className="text-xs uppercase tracking-[0.14em] text-stone"
                onClick={() => {
                  localStorage.removeItem(STORAGE);
                  setConversationId(null);
                  setMessages([]);
                }}
              >
                New
              </button>
              <button onClick={closeChat} aria-label="Close stylist">
                <X size={18} />
              </button>
            </div>
          </header>
          <div ref={scroller} className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
            {messages.length === 0 && (
              <div className="space-y-2">
                <p className="text-sm text-stone">Ask for a piece, an outfit, or a store policy. Recommendations come from what is actually in stock.</p>
                {suggestions.map((suggestion) => (
                  <button key={suggestion} onClick={() => void send(suggestion)} className="block w-full rounded-2xl border border-line bg-white px-3 py-2 text-left text-sm hover:border-ink">
                    {suggestion}
                  </button>
                ))}
              </div>
            )}
            {messages.map((message, index) => (
              <div key={index} className={message.role === "user" ? "ml-8 rounded-2xl bg-ink px-3 py-2 text-sm text-cream" : "mr-4 text-sm"}>
                <p className="whitespace-pre-wrap">{message.content}</p>
                {message.products && message.products.length > 0 && (
                  <div className="mt-3 space-y-2">
                    {message.products.map((product) => (
                      <Link key={product.id} to={product.url || `/products/${product.slug}`} className="flex gap-3 rounded-2xl bg-white p-2">
                        {product.image && <img src={product.image} alt="" className="h-16 w-12 rounded-xl object-cover" />}
                        <span>
                          <span className="block font-medium">{product.name}</span>
                          <span className="text-stone">{formatMoney(product.price)}{product.in_stock === false ? " · Out of stock" : ""}</span>
                        </span>
                      </Link>
                    ))}
                  </div>
                )}
                {message.page && (
                  <Link to={message.page.preview_path} className="mt-3 block rounded-2xl bg-white px-3 py-2">
                    Draft: {message.page.title}
                  </Link>
                )}
              </div>
            ))}
            {pending && <p className="text-sm text-stone">The stylist is looking through the shop…</p>}
          </div>
          <form onSubmit={onSubmit} className="flex gap-2 border-t border-line p-3">
            <input value={text} onChange={(event) => setText(event.target.value)} placeholder="A black hoodie under $60" className="h-11 flex-1 rounded-full border border-line bg-white px-4" />
            <button className="h-11 rounded-full bg-ink px-4 text-sm text-cream" disabled={pending}>
              Send
            </button>
          </form>
        </section>
      )}
    </>
  );
}
