import { FormEvent, useState } from "react";
import { Auth, json, request } from "../api";

interface TokenOut { access_token: string; role: string }

export default function AuthScreen({ onAuth }: { onAuth: (a: Auth) => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [f, setF] = useState({ email: "", password: "", salon_name: "", admin_name: "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      const t = mode === "login"
        ? await request<TokenOut>("/auth/login", undefined, json("POST", { email: f.email, password: f.password }))
        : await request<TokenOut>("/auth/register-salon", undefined, json("POST", f));
      onAuth({ token: t.access_token, role: t.role });
    } catch (x) { setErr((x as Error).message); } finally { setBusy(false); }
  }

  return (
    <main className="grid min-h-full place-items-center p-6">
      <form onSubmit={submit} className="w-full max-w-md space-y-4 rounded-3xl bg-white p-8 shadow-sm">
        <h1 className="font-display text-3xl font-bold">{mode === "login" ? "Salon girişi" : "Salonunu oluştur"}</h1>
        <p className="text-graphite">Tableti salonun hesabıyla bir kez açın. Müşteriler hesap açmadan deneme yapar.</p>
        {mode === "register" && (<>
          <input className="input" placeholder="Salon adı" value={f.salon_name} onChange={set("salon_name")} required minLength={2} />
          <input className="input" placeholder="Yönetici adı" value={f.admin_name} onChange={set("admin_name")} required minLength={2} />
        </>)}
        <input className="input" type="email" placeholder="E-posta" value={f.email} onChange={set("email")} required autoComplete="email" />
        <input className="input" type="password" placeholder="Şifre (en az 8 karakter)" value={f.password} onChange={set("password")} required minLength={mode === "register" ? 8 : 1} autoComplete={mode === "login" ? "current-password" : "new-password"} />
        {err && <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-red-800">{err}</p>}
        <button className="btn btn-primary w-full" disabled={busy}>{busy ? "Bekleyin…" : mode === "login" ? "Giriş yap" : "Salonu oluştur"}</button>
        <button type="button" className="w-full text-graphite underline" onClick={() => setMode(mode === "login" ? "register" : "login")}>
          {mode === "login" ? "Yeni salon kaydı" : "Zaten hesabım var"}
        </button>
      </form>
    </main>
  );
}
