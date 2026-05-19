const API_URL = "http://127.0.0.1:8000/predict";

async function predict(payload) {
  const response = await fetch(API_URL, {
    method: "POST",
    credentials: "omit",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Prediction request failed: ${response.status}`);
  }
  const data = await response.json();
  const probability = Number(data.prob_clickbait);
  if (!Number.isFinite(probability)) {
    throw new Error("Prediction response missing prob_clickbait");
  }
  return probability;
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message || message.type !== "predict-clickbait") {
    return false;
  }

  predict(message.payload)
    .then((probability) => sendResponse({ ok: true, probability }))
    .catch((error) => sendResponse({ ok: false, error: String(error.message || error) }));
  return true;
});
