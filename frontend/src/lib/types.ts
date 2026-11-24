export type User = {
  id: string;
  email: string;
  full_name: string;
  role: "admin" | "customer" | string;
  phone: string | null;
};

export type Category = {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  image_url: string | null;
};

export type ProductCard = {
  id: string;
  slug: string;
  name: string;
  brand: string;
  price: string;
  compare_at_price: string | null;
  currency: string;
  category: { id: string; slug: string; name: string };
  image: string | null;
  colors: string[];
  sizes: string[];
  in_stock: boolean;
  is_new: boolean;
  is_bestseller: boolean;
  is_featured: boolean;
  is_trending: boolean;
  url: string;
  why?: string;
  wishlist_item_id?: string;
};

export type Variant = {
  id: string;
  sku: string;
  size: string;
  color: string;
  color_hex: string;
  price: string;
  quantity: number;
  low_stock: boolean;
  in_stock: boolean;
};

export type ProductDetail = ProductCard & {
  description: string;
  material: string | null;
  care: string | null;
  is_active: boolean;
  images: { id: string; url: string; alt: string; is_primary: boolean }[];
  variants: Variant[];
};

export type Cart = {
  id: string | null;
  item_count: number;
  subtotal: string;
  items: {
    id: string;
    quantity: number;
    unit_price: string;
    line_total: string;
    available: number;
    purchasable: boolean;
    variant: { id: string; sku: string; size: string; color: string; color_hex: string };
    product: { id: string; slug: string; name: string; brand: string; image: string | null; url: string; is_active: boolean };
  }[];
};

export type Order = {
  id: string;
  number: string;
  status: string;
  email: string;
  subtotal: string;
  shipping_fee: string;
  discount: string;
  total: string;
  promo_code: string | null;
  created_at: string;
  shipping_address: Record<string, string | null>;
  payment: { provider: string; status: string; amount: string } | null;
  items: {
    id: string;
    product_name: string;
    sku: string;
    size: string;
    color: string;
    unit_price: string;
    quantity: number;
    image_url: string | null;
  }[];
};

export type Address = {
  id: string;
  label: string;
  full_name: string;
  line1: string;
  line2: string | null;
  city: string;
  region: string;
  postal_code: string;
  country: string;
  phone: string | null;
  is_default: boolean;
};

export type StyleProfile = {
  preferred_sizes: string[];
  favorite_colors: string[];
  favorite_categories: string[];
  preferred_brands: string[];
  style_keywords: string[];
  budget_min: string | null;
  budget_max: string | null;
  notes: string | null;
  opted_out: boolean;
};

export type PageBlock = {
  type: string;
  title?: string;
  heading?: string;
  body?: string;
  subtitle?: string;
  eyebrow?: string;
  image_url?: string;
  alt?: string;
  caption?: string;
  cta_label?: string;
  cta_href?: string;
  tone?: "dark" | "light";
  products?: ProductCard[];
  quotes?: { quote: string; author: string; detail?: string | null }[];
  items?: { question: string; answer: string }[];
};

export type ChatResponse = {
  conversation_id: string;
  reply: string;
  products: ProductCard[];
  page: { id: string; slug: string; title: string; status: string; preview_path: string } | null;
  suggestions: string[];
};
