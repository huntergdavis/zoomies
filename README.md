# Zoomies

Public website, screenshots, and downloadable PlayStation release artifacts for
Zoomies.

- Website: <https://hunterdavis.com/zoomies/>
- Downloads: <https://github.com/huntergdavis/zoomies/releases/latest>

The game engine, build system, and source art are maintained separately in a
private repository. Public releases contain the playable BIN/CUE image,
checksums, and release notes.

## Local browser prototype

The development engine checkout can serve its current BIN/CUE through the
browser player without copying the disc or a PlayStation BIOS into this public
repository:

```sh
cd ~/workspace/pspsps-engine
./scripts/run-web.sh
```

Open the printed `/play/` LAN URL. The prototype uses the pinned EmulatorJS
4.2.3 PCSX-ReARMed core and its HLE BIOS. Rebuild the disc, reload the page, and
the server will expose the new image under a new build identifier.
