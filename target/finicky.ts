const rwRemoveTracking = {
  match: () => true, // Execute rewrite on all incoming urls to make this example easier to understand
  url: (url: URL) => {
    const removeKeysStartingWith = ["utm_", "uta_"]; // Remove all query parameters beginning with these strings
    const removeKeys = ["fbclid", "gclid"]; // Remove all query parameters matching these keys

    const search = url.search
      .split("&")
      .map((parameter) => parameter.split("="))
      .filter(
        ([key]) =>
          !removeKeysStartingWith.some((startingWith) =>
            key.startsWith(startingWith)
          )
      )
      .filter(([key]) => !removeKeys.some((removeKey) => key === removeKey));

    return {
      ...url,
      search: search.map((parameter) => parameter.join("=")).join("&"),
    };
  },
};

const isZoom = (url: URL) =>
  url.hostname.endsWith("zoom.us") && url.pathname.startsWith("/j");

const rwGoogleZoomLinks = {
  match: (url: URL) => {
    const target = url.searchParams.get("q");
    if (
      url.host !== "www.google.com" ||
      url.pathname !== "/url" ||
      target === null
    ) {
      return false;
    }
    try {
      const targetUrl = new URL(target);
      return isZoom(targetUrl);
    } catch (error) {}
    return false;
  },
  url: (url: URL) => {
    const target = url.searchParams.get("q");
    try {
      if (target) {
        return new URL(target);
      }
    } catch (error) {}
    return url;
  },
};

export default {
  defaultBrowser: "Firefox",
  handlers: [
    {
      match: isZoom,
      browser: "us.zoom.xos",
    },
    {
      match: /https:\/\/www\.figma\.com\/(design|file)\/*/,
      browser: "Figma",
    },
    {
      match: finicky.matchHostnames("open.spotify.com"),
      browser: "Spotify",
    },
  ],
  rewrite: [rwRemoveTracking, rwGoogleZoomLinks],
};
