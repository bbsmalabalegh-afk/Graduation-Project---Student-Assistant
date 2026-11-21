// =====================================================
// ربط الواجهات بالسيرفر (Back-End Integration) — عبد الرحمن
// كل الصفحات بتستخدم الملف ده عشان تكلم الـ API
// =====================================================

// لو الصفحة متفتحة من السيرفر نفسه (uvicorn) بنستخدم نفس الدومين،
// ولو متفتحة من Live Server أو كملف مباشر بنكلم السيرفر المحلي على 8000.
const API_BASE = (location.protocol === "file:" || (location.port && location.port !== "8000" && location.hostname.match(/^(localhost|127\.0\.0\.1)$/)))
  ? "http://127.0.0.1:8000"
  : "";

const Auth = {
  get token() {
    try { return localStorage.getItem("ssp_token"); } catch (e) { return null; }
  },
  get user() {
    try { return JSON.parse(localStorage.getItem("ssp_user") || "null"); } catch (e) { return null; }
  },
  save(token, user) {
    try {
      localStorage.setItem("ssp_token", token);
      localStorage.setItem("ssp_user", JSON.stringify(user));
    } catch (e) { /* storage مش متاح */ }
  },
  clear() {
    try { localStorage.removeItem("ssp_token"); localStorage.removeItem("ssp_user"); } catch (e) {}
  },
  requireLogin() {
    if (!this.token) window.location.href = "login.html";
  },
};

// رسالة الخطأ اللي جاية من FastAPI ممكن تكون نص أو List (Validation errors)
function apiErrorMessage(data, status) {
  if (data && typeof data.detail === "string") return data.detail;
  if (data && Array.isArray(data.detail)) return data.detail.map(d => d.msg).join(" | ");
  return "حصل خطأ في الاتصال بالسيرفر (" + status + ")";
}

async function apiRequest(path, { method = "GET", body } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (Auth.token) headers["Authorization"] = "Bearer " + Auth.token;

  let res;
  try {
    res = await fetch(API_BASE + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  } catch (e) {
    throw new Error("السيرفر مش شغال أو مش متاح. اتأكد إنك مشغل uvicorn.");
  }

  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (res.status === 401 && path !== "/api/auth/login") {
    Auth.clear();
    window.location.href = "login.html";
  }
  if (!res.ok) throw new Error(apiErrorMessage(data, res.status));
  return data;
}

const API = {
  login: (email, password) => apiRequest("/api/auth/login", { method: "POST", body: { email, password } }),
  register: (full_name, email, password) => apiRequest("/api/auth/register", { method: "POST", body: { full_name, email, password } }),
  me: () => apiRequest("/api/auth/me"),
  predict: (record) => apiRequest("/api/predict", { method: "POST", body: record }),
  students: (params = "") => apiRequest("/api/students" + params),
  createStudent: (s) => apiRequest("/api/students", { method: "POST", body: s }),
  addRecord: (id, record) => apiRequest(`/api/students/${id}/records`, { method: "POST", body: record }),
  predictStudent: (id, record) => apiRequest(`/api/students/${id}/predict`, { method: "POST", body: record }),
  studentPredictions: (id) => apiRequest(`/api/students/${id}/predictions`),
  stats: () => apiRequest("/api/dashboard/stats"),
};
