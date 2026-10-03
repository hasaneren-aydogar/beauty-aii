import { useEffect, useState } from "react";
import { fetchBlobUrl } from "../api";

export default function BlobImage({ path, token, alt, className }: { path: string; token: string; alt: string; className?: string }) {
  const [src, setSrc] = useState<string>();
  useEffect(() => {
    let url: string | undefined;
    let alive = true;
    fetchBlobUrl(path, token).then((u) => { url = u; if (alive) setSrc(u); }).catch(() => {});
    return () => { alive = false; if (url) URL.revokeObjectURL(url); };
  }, [path, token]);
  return src ? <img src={src} alt={alt} className={className} draggable={false} /> : <div className={`${className ?? ""} bg-blush/50 animate-pulse`} aria-label="Yükleniyor" />;
}
