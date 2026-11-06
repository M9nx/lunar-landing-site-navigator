// Public hostnames only — never put OAuth secrets or tokens here.
// Hub and API require separate GitHub sign-ins (not SSO).
window.NAVIGATOR_CONFIG = {
  apiBaseUrl: "https://api.m9nx.me",
  hubBaseUrl: "https://hub.m9nx.me",
  // Static site path for return links (not a CORS Origin)
  sitePath: "/lunar-landing-site-navigator/"
};
