const sites = {
  shackleton: { name: "Shackleton rim", id: "PROVISIONAL REGION · LOLA SITE04", phase: 0.15, earthPhase: 1.05 },
  malapert: { name: "Malapert Massif", id: "PROVISIONAL REGION · LOLA SITE23", phase: 1.1, earthPhase: 0.35 }
};
const siteA = document.querySelector("#site-a");
const siteB = document.querySelector("#site-b");
const dateInput = document.querySelector("#date");
const timeInput = document.querySelector("#time");
const timeLabel = document.querySelector("#time-label");
const results = document.querySelector("#results");
const sunLine = document.querySelector("#sun-line");
const earthLine = document.querySelector("#earth-line");
const cursorLine = document.querySelector("#cursor-line");
const backendStatus = document.querySelector("#backend-status");

function angle(phase, hour, amplitude, offset = 0) {
  return offset + amplitude * Math.sin((2 * Math.PI * hour / 24) + phase);
}
function toY(deg) {
  const top = 30, bottom = 220, min = -12, max = 15;
  return bottom - ((deg - min) / (max - min)) * (bottom - top);
}
function makePath(phase, amplitude, offset) {
  const points = [];
  for (let hour = 0; hour < 24; hour += 1) {
    const x = 55 + (hour / 23) * 725;
    const y = toY(angle(phase, hour, amplitude, offset));
    points.push((hour === 0 ? "M" : "L") + " " + x.toFixed(1) + " " + y.toFixed(1));
  }
  return points.join(" ");
}
function visibilityText(value) {
  return value > 0 ? ["Above geometric horizon", "positive"] : ["Below geometric horizon", "negative"];
}
function card(site, slot, hour, date) {
  const sun = angle(site.phase, hour, 8.2, -0.7);
  const earth = angle(site.earthPhase, hour, 6.5, -0.3);
  const [sunState, sunClass] = visibilityText(sun);
  const [earthState, earthClass] = visibilityText(earth);
  return `<article class="site-card">
    <div class="site-heading"><div><div class="site-id">${site.id}</div><h2>${site.name}</h2></div><span class="demo-chip">SYNTHETIC</span></div>
    <div class="metrics">
      <div class="metric"><small>Sun elevation · illustrative</small><strong>${sun.toFixed(1)}°</strong><div class="state ${sunClass}">${sunState}</div></div>
      <div class="metric"><small>Earth elevation · illustrative</small><strong>${earth.toFixed(1)}°</strong><div class="state ${earthClass}">${earthState}</div></div>
      <div class="metric"><small>Selected sample time</small><strong>${String(hour).padStart(2,"0")}:00</strong><div class="state">${date}</div></div>
      <div class="metric"><small>Terrain / link model</small><strong>Not included</strong><div class="state">UI demonstration only</div></div>
    </div>
  </article>`;
}
function render() {
  const a = sites[siteA.value], b = sites[siteB.value];
  const hour = Number(timeInput.value);
  const date = dateInput.value || "No date selected";
  timeLabel.textContent = String(hour).padStart(2, "0") + ":00";
  results.innerHTML = card(a, "A", hour, date) + card(b, "B", hour, date);
  sunLine.setAttribute("d", makePath(a.phase, 8.2, -0.7));
  earthLine.setAttribute("d", makePath(a.earthPhase, 6.5, -0.3));
  const x = 55 + (hour / 23) * 725;
  cursorLine.setAttribute("d", `M ${x.toFixed(1)} 25 V 220`);
}
async function updateBackendStatus() {
  const baseUrl = window.NAVIGATOR_CONFIG?.apiBaseUrl?.replace(/\/$/, "");
  if (!baseUrl) {
    backendStatus.className = "backend-status offline";
    backendStatus.textContent = "Backend not connected · showing synthetic demo values only.";
    return;
  }
  try {
    const response = await fetch(`${baseUrl}/health`, { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error("Health endpoint returned an error");
    const health = await response.json();
    backendStatus.className = "backend-status online";
    backendStatus.textContent = health.science_calculations_ready
      ? "API reachable · science readiness reported by API; results still require validation."
      : "API reachable · science calculations are not ready. Values below remain synthetic.";
  } catch {
    backendStatus.className = "backend-status offline";
    backendStatus.textContent = "Backend unavailable · showing synthetic demo values only.";
  }
}
[siteA, siteB, dateInput, timeInput].forEach(control => control.addEventListener("input", render));
render();
updateBackendStatus();
