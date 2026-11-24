import { FormEvent, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ApiError, api, saveSession } from "@/lib/api";
import type { User } from "@/lib/types";

function store(data: { access_token: string; refresh_token: string; user: User }) {
  saveSession({ accessToken: data.access_token, refreshToken: data.refresh_token, user: data.user });
}

export function LoginPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const data = await api<{ access_token: string; refresh_token: string; user: User }>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: form.get("email"), password: form.get("password"), guest_token: localStorage.getItem("atelier-cart") }),
      });
      store(data);
      navigate(params.get("next") || (data.user.role === "admin" ? "/admin" : "/account"));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not sign in");
    }
  }
  return (
    <AuthCard title="Welcome back" error={error} onSubmit={submit} submitLabel="Sign in">
      <Field name="email" type="email" label="Email" />
      <Field name="password" type="password" label="Password" />
      <p className="text-sm text-stone">New here? <Link to="/register" className="link-line">Create an account</Link> · <Link to="/forgot" className="link-line">Forgot password</Link></p>
    </AuthCard>
  );
}

export function RegisterPage() {
  const navigate = useNavigate();
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const data = await api<{ access_token: string; refresh_token: string; user: User }>("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({
          email: form.get("email"),
          password: form.get("password"),
          full_name: form.get("full_name"),
          guest_token: localStorage.getItem("atelier-cart"),
        }),
      });
      store(data);
      navigate("/account");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create the account");
    }
  }
  return (
    <AuthCard title="Create an account" error={error} onSubmit={submit} submitLabel="Register">
      <Field name="full_name" label="Name" />
      <Field name="email" type="email" label="Email" />
      <Field name="password" type="password" label="Password" />
      <p className="text-sm text-stone">Already registered? <Link to="/login" className="link-line">Sign in</Link></p>
    </AuthCard>
  );
}

export function ForgotPage() {
  const [message, setMessage] = useState("");
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const data = await api<{ message: string; reset_token?: string; dev_note?: string }>("/api/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email: form.get("email") }),
      });
      setMessage(data.dev_note || data.message);
      setToken(data.reset_token || "");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start a reset");
    }
  }
  return (
    <AuthCard title="Reset your password" error={error} onSubmit={submit} submitLabel="Send reset">
      <Field name="email" type="email" label="Email" />
      {message && <p className="text-sm">{message}</p>}
      {token && <Link to={`/reset?token=${encodeURIComponent(token)}`} className="text-sm link-line">Continue to choose a new password</Link>}
    </AuthCard>
  );
}

export function ResetPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await api("/api/auth/reset-password", { method: "POST", body: JSON.stringify({ token: params.get("token"), password: form.get("password") }) });
      navigate("/login");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reset the password");
    }
  }
  return (
    <AuthCard title="Choose a new password" error={error} onSubmit={submit} submitLabel="Update password">
      <Field name="password" type="password" label="New password" />
    </AuthCard>
  );
}

function AuthCard({ title, error, onSubmit, submitLabel, children }: { title: string; error: string; onSubmit: (event: FormEvent<HTMLFormElement>) => void; submitLabel: string; children: React.ReactNode }) {
  return (
    <form onSubmit={onSubmit} className="mx-auto max-w-md space-y-4 rounded-[1.8rem] bg-white p-8">
      <h1 className="font-serif text-4xl">{title}</h1>
      {children}
      {error && <p className="text-sm text-wine">{error}</p>}
      <button className="h-11 w-full rounded-full bg-ink text-sm text-cream">{submitLabel}</button>
    </form>
  );
}

function Field({ name, label, type = "text" }: { name: string; label: string; type?: string }) {
  return (
    <label className="block text-sm">
      {label}
      <input name={name} type={type} required className="mt-1 h-11 w-full rounded-2xl border border-line bg-white px-3" />
    </label>
  );
}
