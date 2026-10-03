import { FormEvent, useEffect, useRef, useState } from "react";
import { HairModel, RagAnswer, json, request } from "../api";
import BeforeAfter from "../components/BeforeAfter";

interface Msg { role: "user" | "bot"; text: string }

export default function Result({ token, model, beforeUrl, afterUrl, isMock, onAnother, onFinish }: {
  token: string; model: HairModel; beforeUrl: string; afterUrl: string; isMock: boolean; onAnother: () => void; onFinish: () => void;
}) {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const conv = useRef<string>();
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs]);

  async function ask(text: string) {
    if (!text.trim() || busy) return;
    setMsgs((m) => [...m, { role: "user", text }]); setQ(""); setBusy(true);
    try {
      const r = await request<RagAnswer>("/rag/query", token, json("POST", { question: text, conversation_id: conv.current, hair_model_id: model.id }));
      conv.current = r.conversation_id;
      setMsgs((m) => [...m, { role: "bot", text: r.answer }]);
    } catch (e) { setMsgs((m) => [...m, { role: "bot", text: (e as Error).message }]); } finally { setBusy(false); }
  }
  const submit = (e: FormEvent) => { e.preventDefault(); ask(q); };

  return (
    <main className="grid min-h-full gap-6 p-6 md:grid-cols-[1.2fr_1fr] md:p-10">
      <section className="space-y-4">
        <h1 className="font-display text-4xl font-bold">{model.name}</h1>
        <BeforeAfter before={beforeUrl} after={afterUrl} />
        {isMock && <p className="rounded-xl bg-blush px-4 py-3 text-ink">Önizleme modu: bu sonuç gerçek yapay zekâ çıktısı değil, akışı göstermek içindir.</p>}
        <div className="flex gap-4">
          <button className="btn btn-quiet flex-1" onClick={onAnother}>Başka Model Dene</button>
          <button className="btn btn-primary flex-1" onClick={onFinish}>Bitir ve Fotoğrafı Sil</button>
        </div>
      </section>
      <section className="flex min-h-[28rem] flex-col rounded-3xl bg-white p-5 shadow-sm">
        <h2 className="font-display text-2xl font-semibold">Bu model hakkında sor</h2>
        <div className="my-4 flex-1 space-y-3 overflow-y-auto" aria-live="polite">
          {msgs.length === 0 && (
            <div className="flex flex-wrap gap-2">
              {["Bu saçın fiyatı ne?", "Ne kadar sürer?", "Bunu kim yapıyor?"].map((s) => (
                <button key={s} className="rounded-full border border-ink/15 px-4 py-2 hover:bg-blush/60" onClick={() => ask(s)}>{s}</button>
              ))}
            </div>
          )}
          {msgs.map((m, i) => (
            <p key={i} className={`max-w-[90%] whitespace-pre-line rounded-2xl px-4 py-3 text-lg ${m.role === "user" ? "ml-auto bg-ink text-white" : "bg-pearl"}`}>{m.text}</p>
          ))}
          {busy && <p className="text-graphite">Yanıt hazırlanıyor…</p>}
          <div ref={end} />
        </div>
        <form onSubmit={submit} className="flex gap-2">
          <input className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Sorunuzu yazın" maxLength={1000} aria-label="Sorunuz" />
          <button className="btn btn-primary !px-6" disabled={busy || !q.trim()}>Sor</button>
        </form>
      </section>
    </main>
  );
}
