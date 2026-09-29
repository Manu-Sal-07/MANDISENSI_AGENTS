import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // An empty `package-lock.json` stub sits one directory up (tracked in
  // git, unrelated to this app) with no matching `package.json`. Turbopack's
  // workspace-root auto-detection treated its presence as a second
  // workspace root and inferred *that* directory instead of this one,
  // which silently 404'd every route except `/` — the router was resolving
  // pages against the wrong root's (nonexistent) `app/` directory. Pinning
  // the root explicitly is the fix Next.js's own warning names.
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
