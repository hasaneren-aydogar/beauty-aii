import { useEffect, useMemo, useState } from "react";
import { HairModel, request } from "../api";
import BlobImage from "../components/BlobImage";

export default function Pick({ token, onTry, onBack, busy, error }: {
  token: string; onTry: (m: HairModel) => void; onBack: () => void; busy: boolean; error: string;
}) {
  const [models, setModels] = useState<HairModel[]>();
  const [loadErr, setLoadErr] = useState("");
  const [sel, setSel] = useState<HairModel>();
  const [cat, setCat] = useState("Hepsi");

  useEffect(() => { request<HairModel[]>("/hair-models", token).then(setModels).catch((e) => setLoadErr(e.message)); }, [token]);
  const cats = useMemo(() => ["Hepsi", ...Array.from(new Set((models ?? []).map((m) => m.category).filter(Boolean) as string[]))], [models]);
  const shown = (models ?? []).filter((m) => cat === "Hepsi" || m.category === cat);

  return (
    <main className="flex min-h-full flex-col gap-6 p-6 pb-32 md:p-10 md:pb-32">
      <header className="flex items-center justify-between gap-4">
        <h1 className="font-display text-4xl font-bold">Saç Modeli Seç</h1>
        <button className="text-lg text-graphite underline" onClick={onBack}>← Fotoğrafı değiştir</button>
      </header>
      <div className="flex flex-wrap gap-2" role="tablist">
        {cats.map((c) => (
          <button key={c} role="tab" aria-selected={c === cat} onClick={() => setCat(c)}
                  className={`rounded-full px-5 py-2 text-lg ${c === cat ? "bg-ink text-white" : "bg-white text-ink border border-ink/15"}`}>{c}</button>
        ))}
      </div>
      {loadErr && <p role="alert" className="text-red-800">{loadErr}</p>}
      {models && models.length === 0 && <p className="text-xl text-graphite">Bu salonda henüz saç modeli yok. Yönetim ekranından ekleyin.</p>}
      <ul className="grid grid-cols-2 gap-5 md:grid-cols-3 lg:grid-cols-4">
        {shown.map((m) => (
          <li key={m.id}>
            <button onClick={() => setSel(m)} aria-pressed={sel?.id === m.id}
                    className={`w-full overflow-hidden rounded-3xl bg-white text-left transition ${sel?.id === m.id ? "ring-4 ring-lagoon" : "ring-1 ring-ink/10"}`}>
              {m.image_url && <BlobImage path={m.image_url} token={token} alt={m.name} className="aspect-[4/5] w-full object-cover" />}
              <div className="p-4"><p className="font-display text-xl font-semibold">{m.name}</p>
                <p className="text-graphite">{[m.hair_length, m.hair_type].filter(Boolean).join(" · ")}</p></div>
            </button>
          </li>
        ))}
      </ul>
      <div className="fixed inset-x-0 bottom-0 flex items-center justify-between gap-4 border-t border-ink/10 bg-pearl/95 p-4 backdrop-blur">
        <p className="text-lg">{error ? <span role="alert" className="text-red-800">{error}</span> : sel ? <>Seçilen: <b>{sel.name}</b></> : "Bir model seçin"}</p>
        <button className="btn btn-primary" disabled={!sel || busy} onClick={() => sel && onTry(sel)}>{busy ? "Hazırlanıyor…" : "Saçımı Dene"}</button>
      </div>
    </main>
  );
}
