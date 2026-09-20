// Lógica del frontend de MiniSpider. JavaScript vanilla (sin frameworks):
// solo usa `fetch` para hablar con la API del backend y manipula el DOM
// directamente.

const form = document.getElementById("scan-form");
const targetInput = document.getElementById("target");
const modulesGrid = document.getElementById("modules-grid");
const portsFields = document.getElementById("ports-fields");
const statusLine = document.getElementById("status-line");
const resultsPanel = document.getElementById("results-panel");
const resultsContainer = document.getElementById("results-container");
const exportLinks = document.getElementById("export-links");
const historyBody = document.getElementById("history-body");
const scanButton = document.getElementById("scan-button");

// --- Arma dinámicamente los checkboxes de módulos, a partir de lo que
//     devuelve el backend (así, si en el futuro se agrega un módulo
//     nuevo, el frontend lo muestra solo con tocar el backend). ---------
async function loadModules() {
  const response = await fetch("/api/modules");
  const data = await response.json();

  modulesGrid.innerHTML = "";
  for (const moduleName of data.modules) {
    const isDefault = data.default_modules.includes(moduleName);
    const label = document.createElement("label");
    label.innerHTML = `
      <input type="checkbox" name="modules" value="${moduleName}" ${isDefault ? "checked" : ""}>
      ${moduleName}${moduleName === "ports" ? " (activo)" : ""}
    `;
    modulesGrid.appendChild(label);
  }

  // El módulo de puertos es el único "activo" (genera tráfico real
  // contra el objetivo); mostramos/ocultamos sus opciones extra según
  // si está tildado o no.
  modulesGrid.addEventListener("change", (event) => {
    if (event.target.value === "ports") {
      portsFields.style.display = event.target.checked ? "block" : "none";
    }
  });
}

// --- Carga el historial de scans guardados en la base de datos. -------
async function loadHistory() {
  const response = await fetch("/api/scans");
  const scans = await response.json();

  historyBody.innerHTML = "";
  if (scans.length === 0) {
    historyBody.innerHTML = '<tr><td colspan="4">Todavía no corriste ningún scan.</td></tr>';
    return;
  }

  for (const scan of scans) {
    const row = document.createElement("tr");
    const date = new Date(scan.created_at).toLocaleString();
    row.innerHTML = `
      <td>#${scan.id}</td>
      <td>${scan.target}</td>
      <td>${date}</td>
      <td>
        <a href="#" data-view="${scan.id}">ver</a>
        <a href="/api/scans/${scan.id}/export?format=json">JSON</a>
        <a href="/api/scans/${scan.id}/export?format=csv">CSV</a>
      </td>
    `;
    historyBody.appendChild(row);
  }

  // Delegamos el click de "ver" para no tener que reasignar listeners
  // cada vez que se recarga la tabla.
  historyBody.querySelectorAll("[data-view]").forEach((link) => {
    link.addEventListener("click", async (event) => {
      event.preventDefault();
      const scanId = event.target.getAttribute("data-view");
      const response = await fetch(`/api/scans/${scanId}`);
      const scan = await response.json();
      renderResults(scan);
    });
  });
}

// --- Pinta los resultados de un scan (uno por módulo, colapsable). ----
function renderResults(scan) {
  resultsPanel.style.display = "block";
  resultsContainer.innerHTML = "";
  exportLinks.innerHTML = `
    <a href="/api/scans/${scan.scan_id ?? scan.id}/export?format=json">Exportar JSON</a>
    <a href="/api/scans/${scan.scan_id ?? scan.id}/export?format=csv">Exportar CSV</a>
  `;

  for (const [moduleName, moduleResult] of Object.entries(scan.results)) {
    const hasError = moduleResult && typeof moduleResult === "object" && "error" in moduleResult;

    const details = document.createElement("details");
    details.className = "module-result";
    details.open = hasError; // los que fallaron se muestran ya abiertos

    const summary = document.createElement("summary");
    summary.innerHTML = `
      <span>${moduleName}</span>
      <span class="badge ${hasError ? "error" : "ok"}">${hasError ? "error" : "ok"}</span>
    `;

    const pre = document.createElement("pre");
    pre.textContent = JSON.stringify(moduleResult, null, 2);

    details.appendChild(summary);
    details.appendChild(pre);
    resultsContainer.appendChild(details);
  }

  resultsPanel.scrollIntoView({ behavior: "smooth", block: "start" });
}

// --- Envío del formulario: dispara el scan completo. -------------------
form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const target = targetInput.value.trim();
  if (!target) return;

  const selectedModules = Array.from(
    modulesGrid.querySelectorAll('input[type="checkbox"]:checked')
  ).map((checkbox) => checkbox.value);

  const payload = { target, modules: selectedModules };

  if (selectedModules.includes("ports")) {
    const portsSpec = document.getElementById("ports-spec").value.trim();
    if (portsSpec) payload.ports = portsSpec;
  }

  scanButton.disabled = true;
  statusLine.textContent = `Escaneando ${target}... esto puede tardar unos segundos.`;
  resultsPanel.style.display = "none";

  try {
    const response = await fetch("/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      throw new Error(errorBody.detail || `Error HTTP ${response.status}`);
    }

    const scan = await response.json();
    statusLine.textContent = `Scan #${scan.scan_id} completado para ${scan.target}.`;
    renderResults(scan);
    loadHistory();
  } catch (error) {
    statusLine.textContent = `Error: ${error.message}`;
  } finally {
    scanButton.disabled = false;
  }
});

loadModules();
loadHistory();
