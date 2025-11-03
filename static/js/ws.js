(function () {
  const el = document.getElementById("ws-room-slug");
  if (!el) return;
  const slug = el.getAttribute("data-slug");
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const url = `${proto}://${location.host}/ws/room/${slug}/`;
  let ws;

  async function refreshPollBlock() {
    try {
      const res = await fetch(window.location.href, { headers: { "X-Requested-With": "fetch" } });
      const html = await res.text();
      const tmp = document.createElement("div");
      tmp.innerHTML = html;
      const fresh = tmp.querySelector("#poll-block");
      const block = document.getElementById("poll-block");
      if (fresh && block) block.replaceWith(fresh);
    } catch (e) { console.warn("poll refresh failed", e); }
  }

  function connect() {
    const ws2 = new WebSocket(url);
    ws2.onopen = () => console.log("ws: connected", slug);
    ws2.onclose = () => setTimeout(connect, 1500);
    ws2.onerror = () => {};
    ws2.onmessage = (ev) => {
      let data; try { data = JSON.parse(ev.data); } catch { return; }
      const evt = data.event;

      if (evt === "question.new") {
        const list = document.getElementById("question-list");
        if (!list) return;
        const tmp = document.createElement("div");
        tmp.innerHTML = data.html;
        const card = tmp.firstElementChild;
        if (card) list.prepend(card);
      } else if (evt === "question.update" || evt === "vote.tally") {
        const cardId = `q-${data.id}`;
        const old = document.getElementById(cardId);
        const tmp = document.createElement("div");
        tmp.innerHTML = data.html;
        const fresh = tmp.firstElementChild;
        if (old && fresh) old.replaceWith(fresh);
      } else if (evt === "poll.update") {
        refreshPollBlock();
      }
    };
    ws = ws2;
  }
  connect();
})();
