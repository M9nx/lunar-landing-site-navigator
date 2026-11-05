(function () {
  const DOCS = [
    { file: "RESEARCH_DRAFT.md", title: "Research draft", kicker: "Framing" },
    { file: "RESEARCH_UPDATE.md", title: "Research update", kicker: "Findings" },
    { file: "METHOD_DECISION.md", title: "Method decision", kicker: "Approach" },
    { file: "SOURCES.md", title: "Sources", kicker: "Register" },
    { file: "TEAM_BRIEF.md", title: "Team brief", kicker: "Workflow" },
    { file: "BENCHMARK_PLAN.md", title: "Benchmark plan", kicker: "Evaluation" },
    { file: "DEPLOYMENT.md", title: "Deployment", kicker: "Operations" }
  ];

  const allowed = new Set(DOCS.map((doc) => doc.file));
  const params = new URLSearchParams(location.search);
  const requested = params.get("doc") || "RESEARCH_DRAFT.md";
  const current = allowed.has(requested) ? requested : "RESEARCH_DRAFT.md";
  const meta = DOCS.find((doc) => doc.file === current);

  const navEl = document.getElementById("doc-links");
  const selectEl = document.getElementById("doc-select");
  const articleEl = document.getElementById("doc-article");
  const tocEl = document.getElementById("doc-toc-list");

  function slug(text) {
    return text.toLowerCase().trim()
      .replace(/[^\w\s-]/g, "")
      .replace(/\s+/g, "-")
      .slice(0, 80);
  }

  if (navEl) {
    navEl.innerHTML = DOCS.map((doc) => {
      const currentAttr = doc.file === current ? ' aria-current="page"' : "";
      return `<a href="documents.html?doc=${encodeURIComponent(doc.file)}"${currentAttr}>${doc.title}</a>`;
    }).join("");
  }
  if (selectEl) {
    selectEl.innerHTML = DOCS.map((doc) => {
      const selected = doc.file === current ? " selected" : "";
      return `<option value="${doc.file}"${selected}>${doc.title}</option>`;
    }).join("");
    selectEl.addEventListener("change", () => {
      location.href = `documents.html?doc=${encodeURIComponent(selectEl.value)}`;
    });
  }

  function rewriteMarkdownLinks(container) {
    container.querySelectorAll("a[href]").forEach((anchor) => {
      const href = anchor.getAttribute("href") || "";
      const match = href.match(/^(\.\/)?([A-Z0-9_]+\.md)(#[\w-]+)?$/i);
      if (match) {
        anchor.setAttribute("href", `documents.html?doc=${encodeURIComponent(match[2])}${match[3] || ""}`);
      }
    });
  }

  function addHeadingIds(container) {
    const used = new Set();
    container.querySelectorAll("h1, h2, h3, h4").forEach((heading) => {
      let id = heading.id || slug(heading.textContent || "section");
      let unique = id;
      let n = 2;
      while (used.has(unique)) {
        unique = `${id}-${n}`;
        n += 1;
      }
      used.add(unique);
      heading.id = unique;
    });
  }

  function buildToc(container) {
    if (!tocEl) return;
    const headings = [...container.querySelectorAll("h2, h3")];
    if (!headings.length) {
      tocEl.innerHTML = "<p class='doc-loading'>No sections</p>";
      return;
    }
    tocEl.innerHTML = headings.map((heading) => {
      const indent = heading.tagName === "H3" ? ' style="padding-left:20px"' : "";
      return `<a href="#${heading.id}"${indent}>${heading.textContent}</a>`;
    }).join("");
  }

  function addCopyButtons(container) {
    container.querySelectorAll("pre").forEach((block) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "copy-btn";
      button.textContent = "Copy";
      button.addEventListener("click", async () => {
        const text = block.querySelector("code")?.textContent || block.textContent || "";
        try {
          await navigator.clipboard.writeText(text);
          button.textContent = "Copied";
          setTimeout(() => { button.textContent = "Copy"; }, 1500);
        } catch {
          button.textContent = "Copy failed";
        }
      });
      block.appendChild(button);
    });
  }

  function statusBanner(markdown) {
    const match = markdown.match(/\*\*Status:\*\*\s*(.+)/i) || markdown.match(/\*\*Date checked:\*\*\s*(.+)/i);
    return match ? `<div class="doc-status" role="note">${match[1].replace(/</g, "")}</div>` : "";
  }

  function parseMarkdown(markdown) {
    const parser = window.marked;
    if (!parser) throw new Error("Markdown library did not load");
    if (typeof parser.parse === "function") return parser.parse(markdown, { gfm: true, breaks: false });
    return parser(markdown);
  }

  async function render() {
    document.title = `${meta.title} · Lunar Landing Site Navigator`;
    try {
      const response = await fetch(current, { headers: { Accept: "text/plain, text/markdown" } });
      if (!response.ok) throw new Error(`Could not load ${current}`);
      const markdown = await response.text();
      const rawHtml = parseMarkdown(markdown);
      const safeHtml = window.DOMPurify.sanitize(rawHtml, { USE_PROFILES: { html: true } });
      articleEl.innerHTML = `
        <p class="doc-kicker">${meta.kicker} · Markdown viewer</p>
        ${statusBanner(markdown)}
        ${safeHtml}
      `;
      const firstHeading = articleEl.querySelector("h1");
      if (firstHeading) document.title = `${firstHeading.textContent} · Lunar Landing Site Navigator`;
      addHeadingIds(articleEl);
      rewriteMarkdownLinks(articleEl);
      articleEl.querySelectorAll("table").forEach((table) => {
        const wrap = document.createElement("div");
        wrap.className = "table-wrap";
        table.parentNode.insertBefore(wrap, table);
        wrap.appendChild(table);
      });
      buildToc(articleEl);
      addCopyButtons(articleEl);
      if (location.hash) {
        document.getElementById(location.hash.slice(1))?.scrollIntoView();
      }
    } catch (error) {
      articleEl.innerHTML = `
        <h1>${meta.title}</h1>
        <p class="doc-error">The markdown viewer could not load this note. Open the file from the repository if you are viewing it offline without a local server.</p>
        <p><a href="${current}">Download ${current}</a></p>
      `;
    }
  }

  function start() {
    if (window.marked && window.DOMPurify) {
      render();
      return;
    }
    setTimeout(start, 40);
  }
  start();
})();
