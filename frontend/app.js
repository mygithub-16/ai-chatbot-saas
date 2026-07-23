const root = document.getElementById("root");

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "Request failed");
  }
  return data;
}

if (root) {
  root.innerHTML = `
    <main class="page-section sales-page">
      <section class="hero-band">
        <div class="hero-copy">
          <div class="section-eyebrow">Legacy demo</div>
          <h1>ECHURA</h1>
          <p>AI chatbot SaaS for business support, lead capture, and booking workflows.</p>
        </div>
        <div class="demo-console">
          <h2>Quick chat</h2>
          <div id="legacy-log" class="chat-window"></div>
          <form id="legacy-form" class="chat-form">
            <input id="legacy-message" value="What services do you offer?" />
            <button class="primary-button" type="submit">Send</button>
          </form>
        </div>
      </section>
    </main>
  `;

  const form = document.getElementById("legacy-form");
  const input = document.getElementById("legacy-message");
  const log = document.getElementById("legacy-log");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = input.value.trim();
    if (!message) return;
    log.insertAdjacentHTML("beforeend", `<div class="chat-bubble user">${message}</div>`);
    input.value = "";
    try {
      const data = await postJson("/demo/chat", { message, session_id: "legacy-demo" });
      log.insertAdjacentHTML("beforeend", `<div class="chat-bubble assistant">${data.reply || "I can help with that."}</div>`);
    } catch (error) {
      log.insertAdjacentHTML("beforeend", `<div class="analytics-banner">${error.message}</div>`);
    }
  });
}
