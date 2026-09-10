const CONFIG = {
  githubOwner: "syogesh999",
  githubRepository: "Fibrowser",
  appName: "Fibrowser",
  cacheKey: "fibrowser-latest-release",
  cacheDurationMs: 10 * 60 * 1000,
};
const repositoryUrl = `https://github.com/${CONFIG.githubOwner}/${CONFIG.githubRepository}`;
const apiUrl = `https://api.github.com/repos/${CONFIG.githubOwner}/${CONFIG.githubRepository}/releases/latest`;
const elements = {
  heading: document.querySelector("#release-heading"),
  details: document.querySelector("#release-details"),
  status: document.querySelector("#release-status"),
  download: document.querySelector("#download-button"),
  error: document.querySelector("#release-error"),
  errorMessage: document.querySelector("#error-message"),
  retry: document.querySelector("#retry-button"),
  releaseLink: document.querySelector("#footer-releases-link"),
  year: document.querySelector("#current-year"),
};

function setRepositoryLinks() {
  document.querySelectorAll("[data-repository-link]").forEach((link) => {
    link.href = repositoryUrl;
  });
  elements.releaseLink.href = `${repositoryUrl}/releases`;
  elements.year.textContent = new Date().getFullYear();
}
function setStatus(label, state = "") {
  elements.status.textContent = label;
  elements.status.className = `status-badge ${state}`;
}
function resetDownload() {
  elements.download.href = "#release";
  elements.download.removeAttribute("download");
  elements.download.setAttribute("aria-disabled", "true");
}
function scoreAsset(asset) {
  const name = asset.name.toLowerCase();
  let score = 0;
  if (name.includes("fibrowserinstaller")) score += 140;
  if (name.includes("fibrowserpro")) score += 100;
  if (name.includes("fibrowser")) score += 40;
  if (name.includes("windows") || name.includes("win")) score += 10;
  return score;
}
function selectWindowsAsset(assets = []) {
  return (
    assets
      .filter((asset) => asset && asset.name.toLowerCase().endsWith(".exe"))
      .sort((left, right) => scoreAsset(right) - scoreAsset(left))[0] || null
  );
}
function formatReleaseDate(date) {
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(new Date(date));
}
function escapeHtml(value = "") {
  return String(value).replace(
    /[&<>"']/g,
    (character) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[character],
  );
}

function renderRelease(release) {
  const asset = selectWindowsAsset(release.assets);
  const version = release.tag_name || release.name || "Latest release";
  const releaseDate = escapeHtml(
    formatReleaseDate(release.published_at || release.created_at),
  );
  const assetName = asset ? escapeHtml(asset.name) : "Currently unavailable";
  const releaseUrl = escapeHtml(release.html_url);
  elements.heading.textContent = version;
  elements.error.hidden = true;
  elements.details.hidden = false;
  elements.details.innerHTML = `<div class="release-grid"><div><span class="detail-label">Released</span><span class="detail-value">${releaseDate}</span></div><div><span class="detail-label">Windows download</span><span class="detail-value ${asset ? "" : "muted"}">${assetName}</span></div><div><span class="detail-label">Source</span><span class="detail-value">GitHub Releases</span></div></div><a class="release-link" href="${releaseUrl}" target="_blank" rel="noopener noreferrer">View release notes <span aria-hidden="true">&#8594;</span></a>`;
  if (asset) {
    elements.download.href = asset.browser_download_url;
    elements.download.setAttribute("download", asset.name);
    elements.download.removeAttribute("aria-disabled");
    setStatus("Ready", "ready");
  } else {
    resetDownload();
    setStatus("Unavailable", "warning");
  }
}
function showError(message) {
  resetDownload();
  elements.heading.textContent = "Release check unavailable";
  elements.details.hidden = true;
  elements.error.hidden = false;
  elements.errorMessage.textContent = message;
  setStatus("Try again", "warning");
}
function readCache() {
  try {
    const cached = JSON.parse(localStorage.getItem(CONFIG.cacheKey));
    if (cached && Date.now() - cached.savedAt < CONFIG.cacheDurationMs)
      return cached.release;
  } catch (error) {
    localStorage.removeItem(CONFIG.cacheKey);
  }
  return null;
}
function writeCache(release) {
  try {
    localStorage.setItem(
      CONFIG.cacheKey,
      JSON.stringify({ savedAt: Date.now(), release }),
    );
  } catch (error) {}
}

async function loadRelease(forceRefresh = false) {
  elements.error.hidden = true;
  elements.details.hidden = false;
  elements.heading.textContent = "Checking GitHub...";
  elements.details.innerHTML =
    '<div class="loading-state"><span class="spinner" aria-hidden="true"></span><span>Checking for the latest release...</span></div>';
  setStatus("Loading");
  resetDownload();
  if (!forceRefresh) {
    const cachedRelease = readCache();
    if (cachedRelease) return renderRelease(cachedRelease);
  }
  try {
    const response = await fetch(apiUrl, {
      headers: { Accept: "application/vnd.github+json" },
    });
    if (response.status === 404)
      return showError(
        "No published release is available yet. Please check GitHub for project updates.",
      );
    if (response.status === 403 || response.status === 429)
      return showError(
        "GitHub is temporarily limiting release checks. Please try again shortly.",
      );
    if (!response.ok) throw new Error("Release request failed");
    const release = await response.json();
    writeCache(release);
    renderRelease(release);
  } catch (error) {
    showError(
      "Unable to check the latest release. Please try again or visit GitHub directly.",
    );
  }
}

setRepositoryLinks();
elements.retry.addEventListener("click", () => loadRelease(true));
loadRelease();
