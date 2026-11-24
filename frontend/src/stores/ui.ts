import { create } from "zustand";

type Toast = { id: number; message: string; tone: "ok" | "error" };

type UiState = {
  chatOpen: boolean;
  chatDraft: string;
  toasts: Toast[];
  openChat: (draft?: string) => void;
  closeChat: () => void;
  toast: (message: string, tone?: "ok" | "error") => void;
  dismiss: (id: number) => void;
};

export const useUi = create<UiState>((set) => ({
  chatOpen: false,
  chatDraft: "",
  toasts: [],
  openChat: (draft = "") => set({ chatOpen: true, chatDraft: draft }),
  closeChat: () => set({ chatOpen: false, chatDraft: "" }),
  toast: (message, tone = "ok") => {
    const id = Date.now() + Math.random();
    set((state) => ({ toasts: [...state.toasts, { id, message, tone }] }));
    window.setTimeout(() => {
      set((state) => ({ toasts: state.toasts.filter((toast) => toast.id !== id) }));
    }, 3200);
  },
  dismiss: (id) => set((state) => ({ toasts: state.toasts.filter((toast) => toast.id !== id) })),
}));
