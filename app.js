const repo = "huntergdavis/zoomies";
const releaseRoot = `https://github.com/${repo}/releases/latest`;

fetch(`https://api.github.com/repos/${repo}/releases/latest`, {
  headers: { Accept: "application/vnd.github+json" },
})
  .then((response) => {
    if (!response.ok) {
      throw new Error("release metadata unavailable");
    }
    return response.json();
  })
  .then((release) => {
    document.querySelectorAll("[data-release-version]").forEach((node) => {
      node.textContent = release.tag;
    });
    document.querySelector("#hero-download").href = `${releaseRoot}/download/zoomies-ps1.zip`;
    document.querySelector("#download-link").href = `${releaseRoot}/download/zoomies-ps1.zip`;
    document.querySelector("#bin-link").href = `${releaseRoot}/download/pspsps.bin`;
    document.querySelector("#cue-link").href = `${releaseRoot}/download/pspsps.cue`;
    document.querySelector("#notes-link").href = release.html_url;
    document.querySelector("#checksum-link").href = `${releaseRoot}/download/SHA256SUMS.txt`;
  })
  .catch(() => {
    // The checked-in fallback links remain useful in local static previews.
  });
