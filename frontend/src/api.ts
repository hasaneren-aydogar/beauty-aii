export interface HairModel {
  id: string; name: string; description: string | null; image_url: string | null;
  category: string | null; hair_length: string | null; hair_type: string | null; hair_color: string | null;
}
export interface Service { id: string; name: string; description: string | null; price: number | null; duration_minutes: number | null; hair_model_id: string | null }
export interface Employee { id: string; name: string; title: string | null; specialties: string | null }
export interface Doc { id: string; title: string; content: string; source_type: string }
export interface Auth { token: string; role: string }
export interface RagAnswer { answer: string; conversation_id: string; sources: { title: string; snippet: string }[] }

const API_HOST = import.meta.env.VITE_API_URL || "https://beauty-aii.onrender.com";
const BASE = `${API_HOST.replace(/\/$/, "")}/api/v1`;

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

async function parse(res: Response) {
  if (res.ok) return res.status === 204 ? null : res.json();
  let detail = "Bir hata oluştu";
  try {
    const body = await res.json();
    detail = typeof body.detail === "string" ? body.detail : "Girilen bilgileri kontrol edin";
  } catch { /* keep default */ }
  throw new ApiError(res.status, res.status === 429 ? "Çok fazla deneme yapıldı, biraz bekleyin" : detail);
}

export async function request<T>(path: string, token?: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  return parse(await fetch(BASE + path, { ...init, headers }));
}

export const json = (method: string, body: unknown): RequestInit => ({ method, body: JSON.stringify(body) });

/** Images are protected by the JWT, so we fetch them as blobs. */
export async function fetchBlobUrl(path: string, token: string): Promise<string> {
  const res = await fetch(path.startsWith("/api") ? path : BASE + path, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new ApiError(res.status, "Görsel yüklenemedi");
  return URL.createObjectURL(await res.blob());
}
