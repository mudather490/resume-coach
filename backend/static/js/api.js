/** Tiny fetch wrapper for the same-origin FastAPI app. */

export class ApiError extends Error {
  constructor(message, status = 0, isNetwork = false) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.isNetwork = isNetwork;
  }
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(path, { cache: "no-store", ...options });
  } catch (err) {
    throw new ApiError(
      "Backend unreachable. Start it with `python run_backend.py` and try again.",
      0,
      true
    );
  }

  const contentType = response.headers.get("content-type") || "";
  let payload = null;
  try {
    payload = contentType.includes("application/json")
      ? await response.json()
      : await response.text();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const detail =
      payload && typeof payload === "object" ? payload.detail : payload;
    throw new ApiError(
      detail || `Request failed (HTTP ${response.status}).`,
      response.status
    );
  }

  return payload;
}

export const api = {
  get(path) {
    return request(path);
  },
  post(path, body) {
    return request(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  },
  delete(path) {
    return request(path, { method: "DELETE" });
  },
  upload(path, formData) {
    return request(path, { method: "POST", body: formData });
  },
};
