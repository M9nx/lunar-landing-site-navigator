(function () {
  const root = document.body.dataset.root || "";
  const doc = new URLSearchParams(location.search).get("doc") || "";
  const page = doc === "SOURCES.md"
    ? "sources"
    : doc === "DEPLOYMENT.md"
      ? "deploy"
      : (document.body.dataset.page || "");

  const nav = [
    { id: "overview", href: "", label: "Overview" },
    { id: "prototype", href: "prototype/", label: "Prototype" },
    { id: "research", href: "documents.html?doc=RESEARCH_DRAFT.md", label: "Research" },
    { id: "sources", href: "documents.html?doc=SOURCES.md", label: "Sources" },
    { id: "deploy", href: "documents.html?doc=DEPLOYMENT.md", label: "Deployment" }
  ];

  function headerMarkup() {
    const links = nav.map((item) => {
      const current = item.id === page ? ' aria-current="page"' : "";
      return `<a href="${root}${item.href}"${current}>${item.label}</a>`;
    }).join("");
    return `
      <div class="header-inner">
        <a class="brand" href="${root}">
          <span class="brand-kicker">NASA Space Apps 2026</span>
          <span class="brand-name">Lunar Landing Site Navigator</span>
        </a>
        <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="site-nav" aria-label="Open menu">
          <span></span><span></span><span></span>
        </button>
        <nav id="site-nav" class="site-nav" aria-label="Primary">${links}</nav>
      </div>`;
  }

  function footerMarkup() {
    return `
      <div class="wrap footer-grid">
        <div>
          <div class="footer-brand">Lunar Landing Site Navigator</div>
          <p>A NASA Space Apps Challenge 2026 team workspace for lunar site comparison research. Not an official NASA website.</p>
        </div>
        <div class="footer-col">
          <h2>Workspace</h2>
          <ul>
            <li><a href="${root}prototype/">Interactive prototype</a></li>
            <li><a href="${root}documents.html?doc=RESEARCH_DRAFT.md">Research notes</a></li>
            <li><a href="${root}documents.html?doc=DEPLOYMENT.md">Deployment guide</a></li>
          </ul>
        </div>
        <div class="footer-col">
          <h2>References</h2>
          <ul>
            <li><a href="https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/">Challenge brief</a></li>
            <li><a href="${root}documents.html?doc=SOURCES.md">Source register</a></li>
            <li><a href="${root}documents.html?doc=METHOD_DECISION.md">Method decision</a></li>
          </ul>
        </div>
      </div>
      <div class="wrap footer-legal">Research files remain the source of record. Synthetic demo values are labeled and are not mission results.</div>`;
  }

  const header = document.getElementById("site-header");
  const footer = document.getElementById("site-footer");
  if (header) header.innerHTML = headerMarkup();
  if (footer) footer.innerHTML = footerMarkup();

  const toggle = header?.querySelector(".nav-toggle");
  const navEl = document.getElementById("site-nav");
  toggle?.addEventListener("click", () => {
    const open = navEl.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
  });

  async function updateApiChip(selector) {
    const el = document.querySelector(selector);
    if (!el) return;
    const baseUrl = window.NAVIGATOR_CONFIG?.apiBaseUrl?.replace(/\/$/, "");
    if (!baseUrl) {
      el.className = "status-chip offline";
      el.textContent = "API not connected";
      return;
    }
    try {
      const response = await fetch(`${baseUrl}/health`, { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error("health error");
      const health = await response.json();
      el.className = "status-chip online";
      el.textContent = health.science_calculations_ready
        ? "API reachable · science still requires validation"
        : "API reachable · science calculations not ready";
    } catch {
      el.className = "status-chip offline";
      el.textContent = "API unavailable";
    }
  }

  window.NavigatorSite = { updateApiChip, root };
})();
