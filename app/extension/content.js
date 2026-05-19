(function initializeClickbaitExtension() {
  const API_URL = "http://127.0.0.1:8000/predict";
  const HOVER_DELAY_MS = 400;
  const core = window.VnExpressClickbaitCore;
  if (!core) {
    console.warn("[Clickbait Predictor] content-core.js did not initialize");
    return;
  }
  document.documentElement.dataset.cbxPredictor = "ready";
  const cache = new Map();
  const inflight = new Map();
  let hoverTimer = null;
  let activeTooltip = null;

  function clearHoverTimer() {
    if (hoverTimer) {
      window.clearTimeout(hoverTimer);
      hoverTimer = null;
    }
  }

  function ensureBadge(container) {
    let badge = container.querySelector(":scope > .cbx-badge");
    if (!badge) {
      badge = document.createElement("span");
      badge.className = "cbx-badge cbx-badge-loading";
      badge.textContent = "CB...";
      container.appendChild(badge);
    }
    return badge;
  }

  function ensureTooltip() {
    if (!activeTooltip) {
      activeTooltip = document.createElement("div");
      activeTooltip.className = "cbx-tooltip";
      activeTooltip.setAttribute("role", "status");
      document.documentElement.appendChild(activeTooltip);
    }
    return activeTooltip;
  }

  function positionTooltip(event) {
    const tooltip = ensureTooltip();
    tooltip.style.left = `${event.clientX + 14}px`;
    tooltip.style.top = `${event.clientY + 14}px`;
  }

  function setTooltip(probability, event) {
    const tooltip = ensureTooltip();
    const percentage = (probability * 100).toFixed(1);
    const label = probability >= 0.5 ? "Clickbait" : "Non-clickbait";
    tooltip.textContent = `Clickbait probability: ${percentage}%\nLabel: ${label}`;
    tooltip.dataset.risk = core.getRiskLevel(probability);
    positionTooltip(event);
    tooltip.classList.add("cbx-tooltip-visible");
  }

  function hideTooltip() {
    clearHoverTimer();
    if (activeTooltip) {
      activeTooltip.classList.remove("cbx-tooltip-visible");
    }
  }

  function setBadge(container, probability) {
    const badge = ensureBadge(container);
    const percentage = Math.round(probability * 100);
    badge.textContent = `CB: ${percentage}%`;
    badge.dataset.risk = core.getRiskLevel(probability);
    badge.classList.remove("cbx-badge-loading", "cbx-badge-error");
  }

  function setBadgeError(container) {
    const badge = ensureBadge(container);
    badge.textContent = "CB: ?";
    badge.classList.add("cbx-badge-error");
    badge.classList.remove("cbx-badge-loading");
  }

  async function requestPrediction(article) {
    const key = core.makeCacheKey(article.title, article.lead, article.url);
    if (cache.has(key)) {
      return cache.get(key);
    }
    if (inflight.has(key)) {
      return inflight.get(key);
    }

    const payload = {
        title: article.title,
        lead_paragraph: article.lead,
      };

    const request = sendPredictionMessage(payload)
      .then((probability) => {
        cache.set(key, probability);
        return probability;
      })
      .finally(() => {
        inflight.delete(key);
      });

    inflight.set(key, request);
    return request;
  }

  function sendPredictionMessage(payload) {
    if (typeof chrome !== "undefined" && chrome.runtime && chrome.runtime.sendMessage) {
      return new Promise((resolve, reject) => {
        chrome.runtime.sendMessage({ type: "predict-clickbait", payload }, (response) => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
            return;
          }
          if (!response || !response.ok) {
            reject(new Error(response && response.error ? response.error : "Prediction failed"));
            return;
          }
          resolve(Number(response.probability));
        });
      });
    }

    return fetch(API_URL, {
      method: "POST",
      credentials: "omit",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Prediction request failed: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => Number(data.prob_clickbait));
  }

  function schedulePrediction(event) {
    if (!(event.target instanceof Element)) {
      return;
    }
    const titleTarget = event.target.closest(core.TITLE_SELECTOR);
    if (!titleTarget) {
      return;
    }

    const article = core.extractArticleData(titleTarget);
    if (!article || !article.title) {
      return;
    }
    document.documentElement.dataset.cbxLastHover = article.title;

    clearHoverTimer();
    ensureBadge(article.container);
    positionTooltip(event);
    hoverTimer = window.setTimeout(async () => {
      try {
        const probability = await requestPrediction(article);
        setBadge(article.container, probability);
        setTooltip(probability, event);
      } catch (error) {
        console.warn("[Clickbait Predictor]", error);
        setBadgeError(article.container);
      }
    }, HOVER_DELAY_MS);
  }

  document.addEventListener("mouseover", schedulePrediction, { passive: true });
  document.addEventListener("mousemove", (event) => {
    if (activeTooltip && activeTooltip.classList.contains("cbx-tooltip-visible")) {
      positionTooltip(event);
    }
  }, { passive: true });
  document.addEventListener("mouseout", (event) => {
    if (!event.relatedTarget || !event.target.closest(core.CONTAINER_SELECTOR)) {
      hideTooltip();
    }
  }, { passive: true });

  window.VnExpressClickbaitRuntime = {
    cache,
    inflight,
    requestPrediction,
  };
})();
