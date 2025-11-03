// static/js/ui.js
(function(){
  // Copy-to-clipboard
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-copy]");
    if (!btn) return;
    const text = btn.getAttribute("data-copy") || "";
    navigator.clipboard.writeText(text).then(() => {
      window.showToast && window.showToast("Copied!", "ok");
    }).catch(() => {
      window.showToast && window.showToast("Copy failed", "error");
    });
  });

  // Tiny toast
  const toastBox = document.createElement("div");
  toastBox.className = "fixed bottom-4 right-4 flex flex-col gap-2 z-40";
  document.body.appendChild(toastBox);

  window.showToast = (msg, type="ok") => {
    const el = document.createElement("div");
    el.className = "px-3 py-2 rounded-lg text-sm shadow " +
      (type === "error" ? "bg-red-600 text-white" : "bg-black text-white");
    el.textContent = msg;
    toastBox.appendChild(el);
    setTimeout(() => el.remove(), 2200);
  };
})();
