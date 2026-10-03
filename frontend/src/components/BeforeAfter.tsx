import { useRef, useState } from "react";

/** ÖNCE | SONRA slider: drag the handle, or use arrow keys. */
export default function BeforeAfter({ before, after }: { before: string; after: string }) {
  const [pos, setPos] = useState(50);
  const box = useRef<HTMLDivElement>(null);

  const move = (clientX: number) => {
    const r = box.current!.getBoundingClientRect();
    setPos(Math.min(100, Math.max(0, ((clientX - r.left) / r.width) * 100)));
  };

  return (
    <div
      ref={box}
      className="relative w-full overflow-hidden rounded-3xl bg-ink select-none touch-none"
      style={{ aspectRatio: "4 / 5" }}
      onPointerDown={(e) => { e.currentTarget.setPointerCapture(e.pointerId); move(e.clientX); }}
      onPointerMove={(e) => e.buttons && move(e.clientX)}
    >
      <img src={after} alt="Sonra" className="absolute inset-0 h-full w-full object-cover" draggable={false} />
      <img src={before} alt="Önce" className="absolute inset-0 h-full w-full object-cover" draggable={false}
           style={{ clipPath: `inset(0 ${100 - pos}% 0 0)` }} />
      <span className="absolute left-4 top-4 rounded-full bg-ink/80 px-4 py-1.5 text-sm font-semibold text-white">Önce</span>
      <span className="absolute right-4 top-4 rounded-full bg-lagoon px-4 py-1.5 text-sm font-semibold text-white">Sonra</span>
      <div className="absolute inset-y-0 w-1 bg-white shadow" style={{ left: `calc(${pos}% - 2px)` }}>
        <button
          role="slider" aria-label="Önce sonra karşılaştırma" aria-valuenow={Math.round(pos)} aria-valuemin={0} aria-valuemax={100}
          onKeyDown={(e) => { if (e.key === "ArrowLeft") setPos((p) => Math.max(0, p - 5)); if (e.key === "ArrowRight") setPos((p) => Math.min(100, p + 5)); }}
          className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 h-14 w-14 rounded-full bg-white text-ink shadow-lg text-xl"
        >⇄</button>
      </div>
    </div>
  );
}
