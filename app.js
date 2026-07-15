const repo = "huntergdavis/zoomies";
const releaseRoot = `https://github.com/${repo}/releases/latest`;

function firstAvailableAsset(assetNames, candidates) {
  return candidates.find((candidate) => assetNames.has(candidate)) ?? null;
}

function firstAvailableDiscPair(assetNames) {
  const candidates = [
    { bin: "Zoomies.bin", cue: "Zoomies.cue" },
    { bin: "pspsps.bin", cue: "pspsps.cue" },
  ];
  return candidates.find(
    (candidate) => assetNames.has(candidate.bin) && assetNames.has(candidate.cue),
  ) ?? null;
}

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
    const assetNames = new Set(
      Array.isArray(release.assets)
        ? release.assets.map((asset) => asset.name)
        : [],
    );
    const disc = firstAvailableDiscPair(assetNames);
    const coverName = firstAvailableAsset(assetNames, ["Zoomies-cover.png"]);

    document.querySelectorAll("[data-release-version]").forEach((node) => {
      node.textContent = release.tag_name;
    });
    document.querySelector("#hero-download").href = `${releaseRoot}/download/zoomies-ps1.zip`;
    document.querySelector("#download-link").href = `${releaseRoot}/download/zoomies-ps1.zip`;
    if (disc) {
      document.querySelector("#bin-link").href = `${releaseRoot}/download/${disc.bin}`;
      document.querySelector("#cue-link").href = `${releaseRoot}/download/${disc.cue}`;
      document.querySelector("#disc-filename").textContent = disc.cue;
    }
    if (coverName) {
      const coverLink = document.querySelector("#cover-link");
      coverLink.href = `${releaseRoot}/download/${coverName}`;
      coverLink.hidden = false;
    }
    document.querySelector("#notes-link").href = release.html_url;
    document.querySelector("#checksum-link").href = `${releaseRoot}/download/SHA256SUMS.txt`;
  })
  .catch(() => {
    // The checked-in fallback links remain useful in local static previews.
  });
