(function attachCore(root, factory) {
  const core = factory();
  if (typeof module !== "undefined" && module.exports) {
    module.exports = core;
  }
  root.VnExpressClickbaitCore = core;
})(typeof window !== "undefined" ? window : globalThis, function createCore() {
  const titleSelectors = [".title-news", "h2", "h3", "h4", "a[title]"];
  const descSelectors = [".description", ".lead", ".desc", "p"];
  const containerSelectors = [
    "article",
    ".item-news",
    ".thumb-art",
    ".sub-news",
    ".box-category",
    ".sidebar",
    ".col-left",
    ".col-right",
  ];

  const TITLE_SELECTOR = titleSelectors.join(", ");
  const DESC_SELECTOR = descSelectors.join(", ");
  const CONTAINER_SELECTOR = containerSelectors.join(", ");

  function normalizeText(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }

  function getRiskLevel(probability) {
    if (probability >= 0.7) {
      return "high";
    }
    if (probability >= 0.4) {
      return "medium";
    }
    return "low";
  }

  function makeCacheKey(title, lead, url) {
    const normalizedUrl = normalizeText(url);
    if (normalizedUrl) {
      return normalizedUrl;
    }
    return `${normalizeText(title)}||${normalizeText(lead)}`;
  }

  function isElement(value) {
    return value && typeof value.querySelector === "function";
  }

  function elementMatches(element, selector) {
    return element && typeof element.matches === "function" && element.matches(selector);
  }

  function findTitleElement(container, target) {
    if (elementMatches(target, TITLE_SELECTOR)) {
      return target;
    }
    return container.querySelector(TITLE_SELECTOR);
  }

  function findLead(container, titleElement) {
    const leadElement = container.querySelector(DESC_SELECTOR);
    if (!leadElement || leadElement === titleElement) {
      return "";
    }
    return normalizeText(leadElement.textContent);
  }

  function getUrl(container, titleElement) {
    if (titleElement && titleElement.href) {
      return titleElement.href;
    }
    if (titleElement && typeof titleElement.closest === "function") {
      const titleLink = titleElement.closest("a[href]");
      if (titleLink && titleLink.href) {
        return titleLink.href;
      }
    }
    const link = container.querySelector("a[href]");
    return link && link.href ? link.href : "";
  }

  function extractArticleData(target) {
    if (!isElement(target)) {
      return null;
    }
    const container =
      (typeof target.closest === "function" && target.closest(CONTAINER_SELECTOR)) || target;
    const titleElement = findTitleElement(container, target);
    if (!titleElement) {
      return null;
    }

    const title = normalizeText(titleElement.textContent || titleElement.title);
    if (!title) {
      return null;
    }

    return {
      title,
      lead: findLead(container, titleElement),
      url: getUrl(container, titleElement),
      container,
    };
  }

  function collectCandidateContainers(rootNode) {
    if (!rootNode || typeof rootNode.querySelectorAll !== "function") {
      return [];
    }
    return Array.from(rootNode.querySelectorAll(CONTAINER_SELECTOR))
      .map((container) => extractArticleData(container))
      .filter(Boolean);
  }

  return {
    titleSelectors,
    descSelectors,
    containerSelectors,
    TITLE_SELECTOR,
    DESC_SELECTOR,
    CONTAINER_SELECTOR,
    normalizeText,
    getRiskLevel,
    makeCacheKey,
    extractArticleData,
    collectCandidateContainers,
  };
});
