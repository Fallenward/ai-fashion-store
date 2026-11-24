import { Navigate, Route, Routes } from "react-router-dom";
import { StoreShell } from "@/components/layout/Shell";
import { AccountLayout, AddressesPage, OrdersPage, PreferencesPage, ProfilePage, WishlistPage } from "@/pages/AccountPages";
import { AdminAI, AdminCustomer, AdminCustomers, AdminHome, AdminInbox, AdminLayout, AdminOrderDetail, AdminOrders, AdminPageEditor, AdminPages, AdminProductForm, AdminProducts } from "@/pages/AdminPages";
import { ForgotPage, LoginPage, RegisterPage, ResetPage } from "@/pages/AuthPages";
import { CartPage } from "@/pages/CartPage";
import { CheckoutPage } from "@/pages/CheckoutPage";
import { CmsPage, ContactPage, JournalPage } from "@/pages/ContentPages";
import { HomePage } from "@/pages/HomePage";
import { OrderPage } from "@/pages/OrderPage";
import { ProductPage } from "@/pages/ProductPage";
import { ShopPage } from "@/pages/ShopPage";
import { useSession } from "@/stores/session";

function RequireAdmin({ children }: { children: JSX.Element }) {
  const { user } = useSession();
  if (!user) return <Navigate to="/login?next=/admin" replace />;
  if (user.role !== "admin") return <Navigate to="/" replace />;
  return children;
}

export function App() {
  return (
    <Routes>
      <Route element={<StoreShell />}>
        <Route index element={<HomePage />} />
        <Route path="shop" element={<ShopPage />} />
        <Route path="products/:slug" element={<ProductPage />} />
        <Route path="cart" element={<CartPage />} />
        <Route path="checkout" element={<CheckoutPage />} />
        <Route path="orders/:id" element={<OrderPage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="register" element={<RegisterPage />} />
        <Route path="forgot" element={<ForgotPage />} />
        <Route path="reset" element={<ResetPage />} />
        <Route path="wishlist" element={<WishlistPage />} />
        <Route path="contact" element={<ContactPage />} />
        <Route path="about" element={<CmsPage slug="about" />} />
        <Route path="faq" element={<CmsPage slug="faq" />} />
        <Route path="privacy" element={<CmsPage slug="privacy" />} />
        <Route path="terms" element={<CmsPage slug="terms" />} />
        <Route path="shipping" element={<CmsPage slug="shipping-returns" />} />
        <Route path="pages" element={<JournalPage />} />
        <Route path="pages/:slug" element={<CmsPage />} />
        <Route path="account" element={<AccountLayout />}>
          <Route index element={<ProfilePage />} />
          <Route path="orders" element={<OrdersPage />} />
          <Route path="addresses" element={<AddressesPage />} />
          <Route path="preferences" element={<PreferencesPage />} />
        </Route>
        <Route path="admin" element={<RequireAdmin><AdminLayout /></RequireAdmin>}>
          <Route index element={<AdminHome />} />
          <Route path="products" element={<AdminProducts />} />
          <Route path="products/new" element={<AdminProductForm />} />
          <Route path="products/:id" element={<AdminProductForm />} />
          <Route path="orders" element={<AdminOrders />} />
          <Route path="orders/:id" element={<AdminOrderDetail />} />
          <Route path="customers" element={<AdminCustomers />} />
          <Route path="customers/:id" element={<AdminCustomer />} />
          <Route path="pages" element={<AdminPages />} />
          <Route path="pages/new" element={<AdminPageEditor />} />
          <Route path="pages/:id" element={<AdminPageEditor />} />
          <Route path="ai" element={<AdminAI />} />
          <Route path="messages" element={<AdminInbox />} />
        </Route>
        <Route path="*" element={<div><h1 className="font-serif text-5xl">Page not found</h1></div>} />
      </Route>
    </Routes>
  );
}
