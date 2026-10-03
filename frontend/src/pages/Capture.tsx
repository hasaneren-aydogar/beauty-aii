import { useEffect, useRef, useState } from "react";

export default function Capture({ onPhoto, onBack }: { onPhoto: (file: Blob) => void; onBack: () => void }) {
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream>();
  const [camError, setCamError] = useState("");
  const [shot, setShot] = useState<{ blob: Blob; url: string }>();

  useEffect(() => {
    if (!navigator.mediaDevices?.getUserMedia) { setCamError("Kamera bu tarayıcıda kullanılamıyor. Galeriden seçebilirsiniz."); return; }
    navigator.mediaDevices.getUserMedia({ video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 1280 } }, audio: false })
      .then((s) => { stream.current = s; if (video.current) video.current.srcObject = s; })
      .catch(() => setCamError("Kameraya erişilemedi. İzin verin ya da galeriden seçin."));
    return () => stream.current?.getTracks().forEach((t) => t.stop());
  }, []);

  function snap() {
    const v = video.current!;
    const c = document.createElement("canvas");
    c.width = v.videoWidth; c.height = v.videoHeight;
    const ctx = c.getContext("2d")!;
    ctx.translate(c.width, 0); ctx.scale(-1, 1); // un-mirror the selfie preview
    ctx.drawImage(v, 0, 0);
    c.toBlob((b) => b && setShot({ blob: b, url: URL.createObjectURL(b) }), "image/jpeg", 0.92);
  }

  return (
    <main className="mx-auto flex min-h-full max-w-2xl flex-col gap-6 p-6">
      <button className="self-start text-lg text-graphite underline" onClick={onBack}>← Geri</button>
      <div className="relative aspect-[3/4] overflow-hidden rounded-[2rem] bg-ink">
        {shot ? <img src={shot.url} alt="Çekilen fotoğraf" className="h-full w-full object-cover" /> :
          <video ref={video} autoPlay playsInline muted className="h-full w-full -scale-x-100 object-cover" />}
        {!shot && !camError && <div className="pointer-events-none absolute inset-8 rounded-[999px] border-2 border-dashed border-white/60" aria-hidden />}
        {camError && <p className="absolute inset-0 grid place-items-center p-8 text-center text-lg text-white">{camError}</p>}
      </div>
      <p className="text-center text-graphite">Yüzünüz çerçevede, saçlarınız görünür olsun. Fotoğraf işlem sonrası silinir.</p>
      {shot ? (
        <div className="flex gap-4">
          <button className="btn btn-quiet flex-1" onClick={() => setShot(undefined)}>Tekrar Çek</button>
          <button className="btn btn-primary flex-1" onClick={() => onPhoto(shot.blob)}>Bu Fotoğrafı Kullan</button>
        </div>
      ) : (
        <div className="flex gap-4">
          <button className="btn btn-primary flex-1" onClick={snap} disabled={!!camError}>Fotoğraf Çek</button>
          <label className="btn btn-quiet flex-1 cursor-pointer">Galeriden Seç
            <input type="file" accept="image/jpeg,image/png,image/webp" className="sr-only"
                   onChange={(e) => { const f = e.target.files?.[0]; if (f) setShot({ blob: f, url: URL.createObjectURL(f) }); }} />
          </label>
        </div>
      )}
    </main>
  );
}
