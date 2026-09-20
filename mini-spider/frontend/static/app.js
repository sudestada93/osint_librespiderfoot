// Lógica del frontend de MiniSpider. JavaScript vanilla (sin frameworks):
// solo usa `fetch` para hablar con la API del backend y manipula el DOM
// directamente.

const form = document.getElementById("scan-form");
const targetInput = document.getElementById("target");
const targetTypeHint = document.getElementById("target-type-hint");
const modulesGrid = document.getElementById("modules-grid");
const portsFields = document.getElementById("ports-fields");
const phoneRegionFields = document.getElementById("phone-region-fields");
const statusLine = document.getElementById("status-line");
const resultsPanel = document.getElementById("results-panel");
const resultsContainer = document.getElementById("results-container");
const exportLinks = document.getElementById("export-links");
const historyBody = document.getElementById("history-body");
const scanButton = document.getElementById("scan-button");

// Nombres lindos para mostrarle al usuario (el backend habla en inglés
// técnico: "domain", "email", etc.)
const TARGET_TYPE_LABELS = {
  domain: "dominio",
  ip: "dirección IP",
  email: "email",
  phone: "teléfono",
  username: "username",
};

let allModulesData = null; // cache de GET /api/modules
let currentTargetType = null;

// --- Pinta los checkboxes de módulos para una lista puntual (ya sea la
//     de "todos los módulos" o la filtrada por tipo de target). --------
function renderModulesGrid(moduleNames, defaultModuleNames) {
  modulesGrid.innerHTML = "";
  for (const moduleName of moduleNames) {
    const isDefault = defaultModuleNames.includes(moduleName);
    const label = document.createElement("label");
    label.innerHTML = `
      <input type="checkbox" name="modules" value="${moduleName}" ${isDefault ? "checked" : ""}>
      ${moduleName}${moduleName === "ports" ? " (activo)" : ""}
    `;
    modulesGrid.appendChild(label);
  }
  // Si "ports" no quedó en la lista (target no es domain/ip), ocultamos
  // sus campos extra aunque hayan quedado abiertos de una búsqueda previa.
  if (!moduleNames.includes("ports")) {
    portsFields.style.display = "none";
  }
}

// --- Cada vez que cambia el texto del target, le preguntamos al backend
//     qué tipo de objetivo parece ser, y filtramos los módulos
//     disponibles a los que tienen sentido para ese tipo. Con un
//     "debounce" chico para no spamear al backend en cada tecla. -------
let detectTypeTimer = null;
targetInput.addEventListener("input", () => {
  clearTimeout(detectTypeTimer);
  detectTypeTimer = setTimeout(detectAndFilterModules, 350);
});

async function detectAndFilterModules() {
  const target = targetInput.value.trim();

  if (!target) {
    // Solo tocamos la grilla si veníamos de un tipo detectado distinto
    // a "ninguno" -- si el usuario ya venía sin texto, no hay nada que
    // resetear (y así no pisamos checkboxes que haya tildado a mano).
    if (currentTargetType !== null) {
      currentTargetType = null;
      targetTypeHint.textContent = "";
      phoneRegionFields.style.display = "none";
      if (allModulesData) {
        renderModulesGrid(allModulesData.modules, allModulesData.default_modules);
      }
    }
    return;
  }

  const response = await fetch(`/api/detect-type?target=${encodeURIComponent(target)}`);
  const data = await response.json();

  // Clave para no pisar las elecciones manuales del usuario: si el tipo
  // detectado es el MISMO que ya teníamos, no reconstruimos la grilla
  // de checkboxes (que borraría los tildes/destildes que haya hecho).
  const typeChanged = data.target_type !== currentTargetType;
  currentTargetType = data.target_type;

  const label = TARGET_TYPE_LABELS[data.target_type] || data.target_type;
  targetTypeHint.textContent = `Detectado como: ${label}`;
  phoneRegionFields.style.display = data.target_type === "phone" ? "block" : "none";

  if (typeChanged) {
    renderModulesGrid(data.modules, data.default_modules);
  }
}

// --- Carga inicial de los módulos disponibles (para cuando el campo de
//     target todavía está vacío). ---------------------------------------
async function loadModules() {
  const response = await fetch("/api/modules");
  allModulesData = await response.json();
  renderModulesGrid(allModulesData.modules, allModulesData.default_modules);
}

// El módulo de puertos es el único "activo" (genera tráfico real contra
// el objetivo); mostramos/ocultamos sus opciones extra según si está
// tildado o no. Se escucha una sola vez, por delegación, así sigue
// funcionando aunque renderModulesGrid() reconstruya los checkboxes.
modulesGrid.addEventListener("change", (event) => {
  if (event.target.value === "ports") {
    portsFields.style.display = event.target.checked ? "block" : "none";
  }
});

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

// --- Construye una vista "linda" (con links clicables) para los
//     módulos que devuelven cosas navegables, además del JSON crudo.
//     Para el resto de los módulos, devuelve null (solo se muestra el JSON). ---
function buildActionableView(moduleName, result) {
  if (moduleName === "username_lookup" && result.found_on) {
    if (result.found_on.length === 0) {
      return `<p>No se encontró el username en ninguna de las ${result.total_checked} plataformas chequeadas.</p>`;
    }
    const items = result.found_on
      .map((r) => `<li><a href="${r.url}" target="_blank" rel="noopener noreferrer">${r.platform}</a></li>`)
      .join("");
    return `<p>Encontrado en ${result.found_on.length} de ${result.total_checked} plataformas:</p><ul>${items}</ul>`;
  }

  if (moduleName === "email_lookup" && result.gravatar) {
    const g = result.gravatar;
    return `
      <p>
        <img src="${g.avatar_url}" alt="avatar" width="48" height="48" style="border-radius:50%;vertical-align:middle;margin-right:0.5rem;">
        Perfil público en Gravatar: <a href="${g.profile_url}" target="_blank" rel="noopener noreferrer">${g.display_name || g.profile_url}</a>
      </p>
    `;
  }

  return null;
}

// --- Pinta los resultados de un scan (uno por módulo, colapsable). ----
function renderResults(scan) {
  resultsPanel.style.display = "block";
  resultsContainer.innerHTML = "";
  const scanId = scan.scan_id ?? scan.id;
  exportLinks.innerHTML = `
    <a href="/api/scans/${scanId}/export?format=json">Exportar JSON</a>
    <a href="/api/scans/${scanId}/export?format=csv">Exportar CSV</a>
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
    details.appendChild(summary);

    if (!hasError) {
      const actionable = buildActionableView(moduleName, moduleResult);
      if (actionable) {
        const actionableDiv = document.createElement("div");
        actionableDiv.className = "module-actionable";
        actionableDiv.innerHTML = actionable;
        details.appendChild(actionableDiv);
      }
    }

    const pre = document.createElement("pre");
    pre.textContent = JSON.stringify(moduleResult, null, 2);
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

  if (currentTargetType === "phone") {
    const region = document.getElementById("phone-region").value.trim();
    if (region) payload.phone_region = region.toUpperCase();
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
    statusLine.textContent = `Scan #${scan.scan_id} completado para ${scan.target} (${TARGET_TYPE_LABELS[scan.target_type] || scan.target_type}).`;
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
