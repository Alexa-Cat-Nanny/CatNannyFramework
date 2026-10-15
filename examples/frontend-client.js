// Browser ES module. API keys belong only on the Python server.
export function createCatNannyClient(baseUrl = "http://localhost:8000") {
  const root = baseUrl.replace(/\/$/, "");
  async function request(path, options = {}) {
    const response = await fetch(root + path, options);
    const data = await response.json();
    if (!response.ok) {
      const error = new Error(typeof data.detail === "string" ? data.detail :
        data.detail?.message || "请求未完成，请检查输入或稍后重试。");
      error.status = response.status;
      error.code = data.detail?.code;
      error.detail = data.detail;
      throw error;
    }
    return data;
  }
  function query(params = {}) {
    return new URLSearchParams(Object.entries(params).filter(([, value]) => value != null)).toString();
  }
  return {
    capabilities: () => request("/capabilities"),
    eventTypes: () => request("/event-types"),
    // Make payload.request_id once per turn. Keep the SAME payload for retries.
    sendTurn: (payload) => request("/conversations/turns", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
    conversation: (id) => request(`/conversations/${encodeURIComponent(id)}`),
    messages: (id, params) => request(`/conversations/${encodeURIComponent(id)}/messages?${query(params)}`),
    events: (params) => request(`/events?${query(params)}`),
    event: (id) => request(`/events/${encodeURIComponent(id)}`),
    vetSummary: (params) => request(`/reports/vet-summary?${query(params)}`),
    uploadPhoto: (eventId, file) => {
      const form = new FormData();
      form.append("event_id", eventId);
      form.append("photo", file);
      return request("/photos/upload", { method: "POST", body: form });
    },
  };
}
