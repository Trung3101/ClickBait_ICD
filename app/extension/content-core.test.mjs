import assert from "node:assert/strict";
import test from "node:test";
import core from "./content-core.js";

class FakeElement {
  constructor({ text = "", href = "", title = "", matches = {}, children = [] } = {}) {
    this.textContent = text;
    this.href = href;
    this.title = title;
    this._matches = matches;
    this._children = children;
    this.parentElement = null;
    for (const child of children) {
      child.parentElement = this;
    }
  }

  matches(selector) {
    return Boolean(this._matches[selector]);
  }

  closest(selectorList) {
    const selectors = selectorList.split(",").map((value) => value.trim());
    let current = this;
    while (current) {
      if (selectors.some((selector) => current.matches(selector))) {
        return current;
      }
      current = current.parentElement;
    }
    return null;
  }

  querySelector(selectorList) {
    const selectors = selectorList.split(",").map((value) => value.trim());
    const stack = [...this._children];
    while (stack.length > 0) {
      const next = stack.shift();
      if (selectors.some((selector) => next.matches(selector))) {
        return next;
      }
      stack.push(...next._children);
    }
    return null;
  }
}

test("makeCacheKey prefers URL and normalizes text", () => {
  assert.equal(
    core.makeCacheKey("  Title  ", " Lead text ", "https://vnexpress.net/a"),
    "https://vnexpress.net/a",
  );
  assert.equal(core.makeCacheKey("  Title  ", " Lead text ", ""), "Title||Lead text");
});

test("getRiskLevel maps probability thresholds", () => {
  assert.equal(core.getRiskLevel(0.399), "low");
  assert.equal(core.getRiskLevel(0.4), "medium");
  assert.equal(core.getRiskLevel(0.7), "high");
});

test("extractArticleData reads title and optional lead from VnExpress-like card", () => {
  const title = new FakeElement({
    text: "  Giong loc cuon sap mai ton  ",
    href: "https://vnexpress.net/giong-loc",
    matches: { ".title-news": true },
  });
  const lead = new FakeElement({
    text: "  Con giong loc manh chieu 17/5 gay do hang rao.  ",
    matches: { ".description": true },
  });
  const article = new FakeElement({
    matches: { "article": true },
    children: [title, lead],
  });

  assert.deepEqual(core.extractArticleData(title), {
    title: "Giong loc cuon sap mai ton",
    lead: "Con giong loc manh chieu 17/5 gay do hang rao.",
    url: "https://vnexpress.net/giong-loc",
    container: article,
  });
});

test("extractArticleData supports title-only cards", () => {
  const title = new FakeElement({
    text: "Tin chi co tieu de",
    href: "https://vnexpress.net/title-only",
    matches: { "a[title]": true },
  });
  const article = new FakeElement({ matches: { ".item-news": true }, children: [title] });

  assert.deepEqual(core.extractArticleData(title), {
    title: "Tin chi co tieu de",
    lead: "",
    url: "https://vnexpress.net/title-only",
    container: article,
  });
});
