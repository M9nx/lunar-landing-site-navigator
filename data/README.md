# Local data directory

Place downloaded mission products here for local processing. Keep the original archive names and record source URL, product identifier/version, coordinate reference frame, scale, and checksum in your research notes.

Large mission datasets are intentionally excluded from Git. The Docker API receives this directory read-only at `/app/data`; the optional notebook environment receives it read-only at `/workspace/data`.

No challenge dataset has been validated or bundled yet.
