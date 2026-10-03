export default function Home({ salonName, canManage, onStart, onAdmin, onLogout, error }: {
  salonName: string; canManage: boolean; onStart: () => void; onAdmin: () => void; onLogout: () => void; error: string;
}) {
  return (
    <main className="relative grid min-h-full grid-cols-1 items-center gap-8 p-8 md:grid-cols-2 md:p-16">
      <div className="space-y-8">
        <p className="text-xl text-graphite">{salonName}</p>
        <h1 className="font-display text-5xl font-bold leading-[1.05] md:text-7xl">Yeni saçını<br />önce aynada gör.</h1>
        <p className="max-w-md text-xl text-graphite">Fotoğrafını çek, bir model seç, sonucu hemen karşılaştır.</p>
        <button className="btn btn-primary !px-12 !py-6 !text-2xl" onClick={onStart}>Saçını Denemeye Başla</button>
        {error && <p role="alert" className="max-w-md rounded-xl bg-red-50 px-4 py-3 text-red-800">{error}</p>}
      </div>
      <div className="mx-auto hidden aspect-[3/4] w-full max-w-sm rounded-[999px] border-[10px] border-ink bg-gradient-to-b from-blush to-white md:grid md:place-items-center" aria-hidden>
        <div className="space-y-2 text-center font-display text-3xl text-ink/70"><p>Önce</p><p className="text-lagoon">Sonra</p></div>
      </div>
      <div className="absolute right-4 top-4 flex gap-2">
        {canManage && <button className="btn btn-quiet !px-4 !py-2 !text-base" onClick={onAdmin}>Yönetim</button>}
        <button className="btn btn-quiet !px-4 !py-2 !text-base" onClick={onLogout}>Çıkış</button>
      </div>
    </main>
  );
}
