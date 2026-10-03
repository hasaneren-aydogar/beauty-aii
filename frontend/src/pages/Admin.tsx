import { FormEvent, useCallback, useEffect, useState } from "react";
import { Doc, Employee, HairModel, Service, json, request } from "../api";
import BlobImage from "../components/BlobImage";

type Tab = "models" | "services" | "employees" | "docs";

export default function Admin({ token, role, onBack }: { token: string; role: string; onBack: () => void }) {
  const isAdmin = role === "admin";
  const tabs: [Tab, string][] = [["models", "Saç modelleri"], ["services", "Hizmetler"], ["employees", "Çalışanlar"], ...(isAdmin ? [["docs", "Salon bilgileri"] as [Tab, string]] : [])];
  const [tab, setTab] = useState<Tab>("models");
  return (
    <main className="mx-auto max-w-5xl space-y-6 p-6">
      <header className="flex items-center justify-between">
        <h1 className="font-display text-3xl font-bold">Yönetim</h1>
        <button className="text-lg text-graphite underline" onClick={onBack}>← Ana ekran</button>
      </header>
      <nav className="flex flex-wrap gap-2" role="tablist">
        {tabs.map(([k, l]) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
                  className={`rounded-full px-5 py-2 text-lg ${tab === k ? "bg-ink text-white" : "bg-white border border-ink/15"}`}>{l}</button>
        ))}
      </nav>
      {tab === "models" && <Models token={token} />}
      {tab === "services" && <Services token={token} />}
      {tab === "employees" && <Employees token={token} />}
      {tab === "docs" && <Docs token={token} />}
    </main>
  );
}

function useList<T>(path: string, token: string) {
  const [items, setItems] = useState<T[]>([]);
  const [err, setErr] = useState("");
  const load = useCallback(() => { request<T[]>(path, token).then(setItems).catch((e) => setErr(e.message)); }, [path, token]);
  useEffect(load, [load]);
  return { items, err, setErr, load };
}

const Panel = ({ children }: { children: React.ReactNode }) => <section className="space-y-4 rounded-3xl bg-white p-6 shadow-sm">{children}</section>;
const Err = ({ msg }: { msg: string }) => (msg ? <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-red-800">{msg}</p> : null);

function Models({ token }: { token: string }) {
  const { items, err, setErr, load } = useList<HairModel>("/hair-models", token);
  async function add(e: FormEvent<HTMLFormElement>) {
    e.preventDefault(); setErr("");
    const form = e.currentTarget;
    try { await request("/hair-models", token, { method: "POST", body: new FormData(form) }); form.reset(); load(); }
    catch (x) { setErr((x as Error).message); }
  }
  async function del(id: string) { await request(`/hair-models/${id}`, token, { method: "DELETE" }); load(); }
  return (
    <Panel>
      <form onSubmit={add} className="grid gap-3 md:grid-cols-3">
        <input className="input" name="name" placeholder="Model adı (ör. Bob)" required minLength={2} />
        <input className="input" name="category" placeholder="Kategori (Kısa/Orta/Uzun)" />
        <input className="input" name="hair_length" placeholder="Uzunluk" />
        <input className="input" name="hair_type" placeholder="Saç tipi (düz/dalgalı…)" />
        <input className="input" name="hair_color" placeholder="Renk" />
        <input className="input" type="file" name="image" accept="image/jpeg,image/png,image/webp" required />
        <textarea className="input md:col-span-3" name="description" placeholder="Açıklama" rows={2} />
        <button className="btn btn-primary md:col-span-3">Modeli ekle</button>
      </form>
      <Err msg={err} />
      <ul className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {items.map((m) => (
          <li key={m.id} className="overflow-hidden rounded-2xl border border-ink/10">
            {m.image_url && <BlobImage path={m.image_url} token={token} alt={m.name} className="aspect-[4/5] w-full object-cover" />}
            <div className="flex items-center justify-between p-3"><span className="font-semibold">{m.name}</span>
              <button className="text-red-700 underline" onClick={() => del(m.id)}>Sil</button></div>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

function Services({ token }: { token: string }) {
  const { items, err, setErr, load } = useList<Service>("/services", token);
  const models = useList<HairModel>("/hair-models", token).items;
  async function add(e: FormEvent<HTMLFormElement>) {
    e.preventDefault(); setErr("");
    const f = new FormData(e.currentTarget); const form = e.currentTarget;
    const num = (k: string) => (f.get(k) ? Number(f.get(k)) : null);
    try {
      await request("/services", token, json("POST", { name: f.get("name"), description: f.get("description") || null,
        price: num("price"), duration_minutes: num("duration_minutes"), hair_model_id: f.get("hair_model_id") || null }));
      form.reset(); load();
    } catch (x) { setErr((x as Error).message); }
  }
  async function del(id: string) { await request(`/services/${id}`, token, { method: "DELETE" }); load(); }
  return (
    <Panel>
      <form onSubmit={add} className="grid gap-3 md:grid-cols-4">
        <input className="input md:col-span-2" name="name" placeholder="Hizmet adı (ör. Bob kesim)" required minLength={2} />
        <input className="input" name="price" type="number" min={0} step="0.01" placeholder="Fiyat (TL)" />
        <input className="input" name="duration_minutes" type="number" min={1} placeholder="Süre (dk)" />
        <select className="input md:col-span-2" name="hair_model_id" defaultValue=""><option value="">Bağlı saç modeli (isteğe bağlı)</option>
          {models.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}</select>
        <input className="input md:col-span-2" name="description" placeholder="Açıklama" />
        <button className="btn btn-primary md:col-span-4">Hizmeti ekle</button>
      </form>
      <Err msg={err} />
      <ul className="divide-y divide-ink/10">
        {items.map((s) => (
          <li key={s.id} className="flex items-center justify-between py-3">
            <span><b>{s.name}</b> <span className="text-graphite">{s.price != null && `${s.price} TL`}{s.duration_minutes && ` · ${s.duration_minutes} dk`}</span></span>
            <button className="text-red-700 underline" onClick={() => del(s.id)}>Sil</button>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

function Employees({ token }: { token: string }) {
  const { items, err, setErr, load } = useList<Employee>("/employees", token);
  async function add(e: FormEvent<HTMLFormElement>) {
    e.preventDefault(); setErr("");
    const f = new FormData(e.currentTarget); const form = e.currentTarget;
    try { await request("/employees", token, json("POST", { name: f.get("name"), title: f.get("title") || null, specialties: f.get("specialties") || null })); form.reset(); load(); }
    catch (x) { setErr((x as Error).message); }
  }
  async function del(id: string) { await request(`/employees/${id}`, token, { method: "DELETE" }); load(); }
  return (
    <Panel>
      <form onSubmit={add} className="grid gap-3 md:grid-cols-3">
        <input className="input" name="name" placeholder="Ad soyad" required minLength={2} />
        <input className="input" name="title" placeholder="Unvan" />
        <input className="input" name="specialties" placeholder="Uzmanlık (ör. Bob, Pixie)" />
        <button className="btn btn-primary md:col-span-3">Çalışanı ekle</button>
      </form>
      <Err msg={err} />
      <ul className="divide-y divide-ink/10">
        {items.map((m) => (
          <li key={m.id} className="flex items-center justify-between py-3">
            <span><b>{m.name}</b> <span className="text-graphite">{m.title} {m.specialties && `· ${m.specialties}`}</span></span>
            <button className="text-red-700 underline" onClick={() => del(m.id)}>Sil</button>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

function Docs({ token }: { token: string }) {
  const { items, err, setErr, load } = useList<Doc>("/rag/documents", token);
  async function add(e: FormEvent<HTMLFormElement>) {
    e.preventDefault(); setErr("");
    const f = new FormData(e.currentTarget); const form = e.currentTarget;
    try { await request("/rag/documents", token, json("POST", { title: f.get("title"), content: f.get("content") })); form.reset(); load(); }
    catch (x) { setErr((x as Error).message); }
  }
  async function del(id: string) { await request(`/rag/documents/${id}`, token, { method: "DELETE" }); load(); }
  return (
    <Panel>
      <p className="text-graphite">Müşterilerin sorularına bu bilgilerle yanıt verilir. Fiyat, süre ve çalışan bilgilerini düz cümlelerle yazın.</p>
      <form onSubmit={add} className="space-y-3">
        <input className="input" name="title" placeholder="Başlık (ör. Randevu kuralları)" required minLength={2} />
        <textarea className="input" name="content" rows={4} placeholder="Bob kesim 2.500 TL'dir. İşlem yaklaşık 90 dakika sürmektedir." required minLength={3} />
        <button className="btn btn-primary">Bilgiyi ekle</button>
      </form>
      <Err msg={err} />
      <ul className="divide-y divide-ink/10">
        {items.map((d) => (
          <li key={d.id} className="flex items-start justify-between gap-4 py-3">
            <span><b>{d.title}</b> <span className="text-graphite">({d.source_type})</span><br />{d.content}</span>
            <button className="text-red-700 underline" onClick={() => del(d.id)}>Sil</button>
          </li>
        ))}
      </ul>
    </Panel>
  );
}
