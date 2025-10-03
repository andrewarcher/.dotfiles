const rwRemoveTracking = {
    match: () => true, // Execute rewrite on all incoming urls to make this example easier to understand
    url: ({url}) => {
        const removeKeysStartingWith = ["utm_", "uta_"]; // Remove all query parameters beginning with these strings
        const removeKeys = ["fbclid", "gclid"]; // Remove all query parameters matching these keys

        const search = url.search
            .split("&")
            .map((parameter) => parameter.split("="))
            .filter(([key]) => !removeKeysStartingWith.some((startingWith) => key.startsWith(startingWith)))
            .filter(([key]) => !removeKeys.some((removeKey) => key === removeKey));

        return {
            ...url,
            search: search.map((parameter) => parameter.join("=")).join("&"),
        };
    },
};

const rwZoomLinks = {
    match: (url) => url.host.includes("zoom.us") && url.pathname.includes("/j/"),
    url: (url) => {
      try {
        const match = url.search.match(/pwd=(\w*)/);
        var pass = match ? '&pwd=' + match[1] : '';
      } catch {
        var pass = "";
      }
      const pathMatch = url.pathname.match(/\/j\/(\d+)/);
      var conf = 'confno=' + (pathMatch ? pathMatch[1] : '');
      url.search = conf + pass;
      url.pathname = '/join';
      url.protocol = "zoommtg";
      return url;
    }
  };

export default {
  defaultBrowser: "Firefox",
  handlers: [
    {
      match: /zoom\.us\/j/,
      browser: "us.zoom.xos"
    },
    {
      match: /https:\/\/www\.figma\.com\/(design|file)\/*/,
      browser: "Figma",
    },
  ],
  rewrite: [
    rwRemoveTracking,
    rwZoomLinks
  ]
};
