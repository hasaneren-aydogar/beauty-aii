import { useEffect, useState } from "react";
import { Auth, HairModel, json, request, fetchBlobUrl } from "./api";
import Admin from "./pages/Admin";
import AuthScreen from "./pages/AuthScreen";
import Capture from "./pages/Capture";
import Home from "./pages/Home";
import Pick from "./pages/Pick";
import Result from "./pages/Result";

type Screen = "home" | "capture" | "pick" | "result" | "admin";
interface TryOut { generated_image_id: string; is_mock: boolean }

export default function App() {
  const [staff, setStaff] = useState<Auth | null>(() => {
    const raw = sessionStorage.getItem("staff");
    return raw ? JSON.parse(raw) : null;
  });
  const [kiosk, setKiosk] = useState<Auth | null>(null); // short-lived customer token
  const [screen, setScreen] = useState<Screen>("home");
  const [salonName, setSalonName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [uploadId, setUploadId] = useState<string>();
  const [beforeUrl, setBeforeUrl] = useState<string>();
  const [result, setResult] = useState<{ model: HairModel; afterUrl: string; isMock: boolean }>();

  useEffect(() => {
    if (!staff) return;
    request<{ name: string }>("/salon", staff.token).then((s) => setSalonName(s.name)).catch(() => logout());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [staff]);

  function login(a: Auth) { sessionStorage.setItem("staff", JSON.stringify(a)); setStaff(a); }
  function logout() { sessionStorage.removeItem("staff"); setStaff(null); setKiosk(null); setScreen("home"); }

  async function start() {
    setError("");
    try {
      const k = await request<{ access_token: string; role: string }>("/auth/kiosk-token", staff!.token, { method: "POST" });
      setKiosk({ token: k.access_token, role: k.role });
      setScreen("capture");
    } catch (e) { setError((e as Error).message); }
  }

  async function onPhoto(blob: Blob) {
    setBusy(true); setError("");
    try {
      const fd = new FormData(); fd.append("file", blob, "photo.jpg");
      const up = await request<{ upload_id: string }>("/image/upload", kiosk!.token, { method: "POST", body: fd });
      setUploadId(up.upload_id);
      setBeforeUrl(await fetchBlobUrl(`/image/${up.upload_id}`, kiosk!.token));
      setScreen("pick");
    } catch (e) { setError((e as Error).message); setScreen("home"); } finally { setBusy(false); }
  }

  async function tryHair(model: HairModel) {
    setBusy(true); setError("");
    try {
      const r = await request<TryOut>("/hair/try", kiosk!.token, json("POST", { upload_id: uploadId, hair_model_id: model.id }));
      const afterUrl = await fetchBlobUrl(`/hair/result/${r.generated_image_id}`, kiosk!.token);
      setResult({ model, afterUrl, isMock: r.is_mock });
      setScreen("result");
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  async function finish() {
    if (kiosk && uploadId) await request(`/image/${uploadId}`, kiosk.token, { method: "DELETE" }).catch(() => {});
    if (beforeUrl) URL.revokeObjectURL(beforeUrl);
    if (result) URL.revokeObjectURL(result.afterUrl);
    setUploadId(undefined); setBeforeUrl(undefined); setResult(undefined); setKiosk(null); setError(""); setScreen("home");
  }

  if (!staff) return <AuthScreen onAuth={login} />;
  if (screen === "admin") return <Admin token={staff.token} role={staff.role} onBack={() => setScreen("home")} />;
  if (screen === "capture" && kiosk) return busy ? <p className="p-10 text-xl">Fotoğraf yükleniyor…</p> : <Capture onPhoto={onPhoto} onBack={finish} />;
  if (screen === "pick" && kiosk && beforeUrl) return <Pick token={kiosk.token} onTry={tryHair} onBack={() => setScreen("capture")} busy={busy} error={error} />;
  if (screen === "result" && kiosk && beforeUrl && result)
    return <Result token={kiosk.token} model={result.model} beforeUrl={beforeUrl} afterUrl={result.afterUrl} isMock={result.isMock}
                   onAnother={() => { URL.revokeObjectURL(result.afterUrl); setScreen("pick"); }} onFinish={finish} />;
  return <Home salonName={salonName} canManage onStart={start} onAdmin={() => setScreen("admin")} onLogout={logout} error={error} />;
}
