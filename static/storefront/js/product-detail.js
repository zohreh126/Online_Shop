const API_BASE = "/api/v1/";
const t = (key) => window.NexoraI18n?.t(key) || key;
const number = (value) => new Intl.NumberFormat(window.NexoraI18n?.current() === "en" ? "en-US" : "fa-IR").format(value);
const money = (value) => window.NexoraI18n?.current() === "en" ? `${new Intl.NumberFormat("en-US").format(Math.round(Number(value)))} toman` : `${number(Math.round(Number(value)))} تومان`;
const format = (key, values) => Object.entries(values).reduce((text, [name, value]) => text.replaceAll(`{${name}}`, value), t(key));
const escapeHTML = (value) => String(value ?? "").replace(/[&<>\'\"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character]));
const slug = window.location.pathname.split("/").filter(Boolean).pop();
const RECENT_STORAGE_KEY = "nexora-recently-viewed";
let productReviews = [];
let reviewUser = null;
let reviewSummary = { average: 0, count: 0, distribution: {}, loaded: false };
let reviewSort = "newest";
let productQuestions = [];
let questionUser = null;
let productRecommendations = [];
let productWatch = null;
let productWatchLoaded = false;

function rememberProduct(product) {
  try {
    const entries = JSON.parse(localStorage.getItem(RECENT_STORAGE_KEY) || "[]");
    const normalized = Array.isArray(entries) ? entries : [];
    const current = normalized.filter((entry) => {
      const id = typeof entry === "object" ? entry.id : entry;
      return Number(id) !== Number(product.id);
    });
    current.unshift({ id: product.id, slug: product.slug });
    localStorage.setItem(RECENT_STORAGE_KEY, JSON.stringify(current.slice(0, 8)));
  } catch (error) {
    // Recently viewed is an enhancement; private browsing must not break the page.
  }
}

function recommendationDiscountLabel(product) {
  const amount = Number(product.discount_amount || 0);
  if (!amount) return "";
  if (product.discount_type === "percentage" && product.discount_value !== null && product.discount_value !== undefined) {
    return format("discountPercent", { percent: number(Number(product.discount_value)) });
  }
  return format("discountAmount", { amount: money(amount) });
}

function recommendationSavingsMarkup(product) {
  const amount = Number(product.discount_amount || 0);
  if (!amount) return "";
  return `<small class="product-savings"><span aria-hidden="true">✦</span>${escapeHTML(format("youSave", { amount: money(amount) }))}</small>`;
}

function discountEndsTimestamp(product) {
  const timestamp = Date.parse(product.discount_ends_at || "");
  return Number.isFinite(timestamp) && timestamp > 0 ? timestamp : 0;
}

function discountCountdownMarkup(product) {
  const endsAt = discountEndsTimestamp(product);
  if (!endsAt || Number(product.discount_amount || 0) <= 0) return "";
  return `<small class="discount-countdown" data-discount-countdown="${endsAt}"><span aria-hidden="true">◷</span><span></span></small>`;
}

function discountCountdownText(milliseconds) {
  const totalSeconds = Math.max(0, Math.floor(milliseconds / 1000));
  const values = [
    ["countdownDay", Math.floor(totalSeconds / 86400)],
    ["countdownHour", Math.floor((totalSeconds % 86400) / 3600)],
    ["countdownMinute", Math.floor((totalSeconds % 3600) / 60)],
    ["countdownSecond", totalSeconds % 60],
  ].filter(([, value]) => value > 0).slice(0, 2);
  if (!values.length) values.push(["countdownSecond", 0]);
  return values.map(([label, value]) => `${number(value)} ${t(label)}`).join(" ");
}

function updateDiscountCountdowns() {
  document.querySelectorAll("[data-discount-countdown]").forEach((element) => {
    const remaining = Number(element.dataset.discountCountdown) - Date.now();
    if (remaining <= 0) {
      element.classList.add("expired");
      element.innerHTML = `<span aria-hidden="true">!</span><span>${escapeHTML(t("discountEnded"))}</span>`;
      return;
    }
    element.classList.remove("expired");
    element.innerHTML = `<span aria-hidden="true">◷</span><span>${escapeHTML(format("discountEndsIn", { time: discountCountdownText(remaining) }))}</span>`;
  });
}

function renderRecommendations() {
  const section = document.querySelector("#product-recommendations");
  const grid = document.querySelector("#product-recommendations-grid");
  if (!section || !grid) return;

  section.hidden = !productRecommendations.length;
  if (!productRecommendations.length) {
    grid.innerHTML = "";
    return;
  }

  grid.innerHTML = productRecommendations.map((product, index) => {
    const name = window.NexoraI18n?.productName(product) || product.name;
    const category = window.NexoraI18n?.category(product.category?.slug, product.category?.name || t("digitalAccessories")) || t("digitalAccessories");
    const url = `/products/${encodeURIComponent(product.slug)}/`;
    const discount = recommendationDiscountLabel(product);
    const image = product.image_url
      ? `<img src="${escapeHTML(product.image_url)}" alt="${escapeHTML(name)}" loading="lazy">`
      : `<span class="recommendation-placeholder">${escapeHTML((product.brand || "N").slice(0, 1))}</span>`;
    const addLabel = t("addToCart");
    return `<article class="product-card recommendation-card" style="--delay:${index * 60}ms"><div class="product-visual"><a class="recommendation-visual-link" href="${url}" aria-label="${escapeHTML(name)}">${image}</a>${discount ? `<span class="discount-badge">${escapeHTML(discount)}</span>` : ""}<span class="stock-badge ${product.is_in_stock ? "" : "out-of-stock"}">${escapeHTML(product.is_in_stock ? t("available") : t("unavailable"))}</span><button class="heart-button" data-favorite-product="${product.id}" aria-label="${escapeHTML(t("addToFavorites"))}" type="button">♡</button></div><div class="product-info"><p class="product-category">${escapeHTML(category)}</p><h3><a class="product-title-link" href="${url}">${escapeHTML(name)}</a></h3><div class="product-bottom"><div class="price-stack"><strong>${escapeHTML(money(product.final_price))}</strong>${Number(product.discount_amount) > 0 ? `<del>${escapeHTML(money(product.price))}</del>${recommendationSavingsMarkup(product)}${discountCountdownMarkup(product)}` : ""}</div><div class="recommendation-actions"><button class="add-button cart-icon-button recommendation-add-button" data-recommendation-cart="${product.id}" type="button" aria-label="${escapeHTML(addLabel)}" title="${escapeHTML(addLabel)}" ${product.is_in_stock ? "" : "disabled"}><span data-recommendation-cart-icon aria-hidden="true">${product.is_in_stock ? "🛒" : "−"}</span></button><a class="recommendation-link" href="${url}"><span>${escapeHTML(t("viewProduct"))}</span><span aria-hidden="true">↗</span></a></div></div></div></article>`;
  }).join("");

  window.NexoraFavorites?.bindButtons(grid);
  grid.querySelectorAll(".recommendation-add-button").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.preventDefault();
      event.stopPropagation();
      const product = productRecommendations.find((item) => Number(item.id) === Number(button.dataset.recommendationCart));
      if (!product || button.disabled) return;
      button.disabled = true;
      button.classList.add("is-loading");
      const icon = button.querySelector("[data-recommendation-cart-icon]");
      try {
        await addToCart(product);
        if (icon) icon.textContent = "✓";
        window.setTimeout(() => { if (icon) icon.textContent = "🛒"; }, 900);
      } catch (error) {
        showToast(error.message || t("operationFailed"));
      } finally {
        button.disabled = false;
        button.classList.remove("is-loading");
      }
    });
  });
  grid.querySelectorAll(".recommendation-card").forEach((card) => card.addEventListener("click", (event) => {
    if (event.target.closest("button, a")) return;
    window.location.href = card.querySelector(".product-title-link")?.getAttribute("href") || "/";
  }));
  updateDiscountCountdowns();
}

async function loadRecommendations(product) {
  const categorySlug = product.category?.slug;
  if (!categorySlug) return;

  try {
    const categoryData = await getJSON(`products/?category=${encodeURIComponent(categorySlug)}&page_size=8`);
    let candidates = Array.isArray(categoryData.results) ? categoryData.results : categoryData;
    candidates = candidates.filter((item) => Number(item.id) !== Number(product.id));
    if (candidates.length < 4) {
      const allData = await getJSON("products/?page_size=100");
      const allProducts = Array.isArray(allData.results) ? allData.results : allData;
      candidates = [...candidates, ...allProducts.filter((item) => Number(item.id) !== Number(product.id) && !candidates.some((candidate) => Number(candidate.id) === Number(item.id)))];
    }
    productRecommendations = candidates
      .sort((first, second) => (Number(second.rating_count || 0) - Number(first.rating_count || 0)) || (Number(second.discount_amount || 0) - Number(first.discount_amount || 0)))
      .slice(0, 4);
    renderRecommendations();
  } catch (error) {
    productRecommendations = [];
    renderRecommendations();
  }
}

async function getJSON(path) {
  const response = await fetch(`${API_BASE}${path}`, { credentials: "same-origin" });
  if (!response.ok) throw new Error("product-not-found");
  return response.json();
}

function getCookie(name) {
  const value = document.cookie.split("; ").find((item) => item.startsWith(`${name}=`));
  return value ? decodeURIComponent(value.slice(name.length + 1)) : null;
}

async function csrf() {
  if (getCookie("csrftoken")) return getCookie("csrftoken");
  const response = await fetch(`${API_BASE}auth/csrf/`, { credentials: "same-origin" });
  if (!response.ok || !getCookie("csrftoken")) throw new Error(t("securityTokenFailed"));
  return getCookie("csrftoken");
}

async function addToCart(product) {
  const response = await fetch(`${API_BASE}cart/items/`, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRFToken": await csrf() }, body: JSON.stringify({ product_id: product.id, quantity: 1 }) });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || data.product_id?.[0] || t("operationFailed"));
  await window.NexoraCartNav?.refresh();
  showToast(t("productAdded"));
}

function updateProductWatchButton(product) {
  const button = document.querySelector("#product-watch-button");
  const hint = document.querySelector("#product-watch-hint");
  if (!button) return;

  const active = Boolean(productWatch?.is_active);
  const label = button.querySelector("[data-watch-label]");
  button.disabled = !productWatchLoaded;
  button.classList.toggle("is-active", active);
  button.classList.toggle("is-loading", !productWatchLoaded);
  button.setAttribute("aria-pressed", String(active));
  button.setAttribute("aria-label", t(active ? "stopWatching" : "watchProduct"));
  button.title = t(active ? "stopWatching" : "watchProduct");
  if (label) label.textContent = t(active ? "stopWatching" : "watchProduct");
  if (hint) hint.textContent = t("watchHint");
  if (!productWatchLoaded && label) label.textContent = t("watchLoading");
  if (productWatchLoaded && product) button.dataset.productId = product.id;
}

async function loadProductWatch(product) {
  const button = document.querySelector("#product-watch-button");
  if (!button) return;

  productWatchLoaded = false;
  updateProductWatchButton(product);
  try {
    const response = await fetch(`${API_BASE}auth/product-watches/?page_size=100`, { credentials: "same-origin" });
    if (response.status === 401 || response.status === 403) {
      productWatch = null;
      return;
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || t("productWatchLoadFailed"));
    const watches = data.results || data || [];
    productWatch = watches.find((watch) => Number(watch.product?.id) === Number(product.id)) || null;
  } catch (error) {
    productWatch = null;
  } finally {
    productWatchLoaded = true;
    updateProductWatchButton(product);
  }
}

async function toggleProductWatch(product) {
  const button = document.querySelector("#product-watch-button");
  if (!button) return;
  button.disabled = true;
  try {
    if (productWatch?.id) {
      const response = await fetch(`${API_BASE}auth/product-watches/${productWatch.id}/`, {
        method: "DELETE",
        credentials: "same-origin",
        headers: { "X-CSRFToken": await csrf() },
      });
      if (response.status === 401 || response.status === 403) {
        window.location.href = `/account/?next=${encodeURIComponent(window.location.pathname)}`;
        return;
      }
      if (!response.ok) throw new Error(t("operationFailed"));
      productWatch = null;
      showToast(t("watchRemoved"));
    } else {
      const response = await fetch(`${API_BASE}auth/product-watches/`, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": await csrf() },
        body: JSON.stringify({ product_id: product.id, notify_price_drop: true, notify_restock: true }),
      });
      const data = await response.json().catch(() => ({}));
      if (response.status === 401 || response.status === 403) {
        window.location.href = `/account/?next=${encodeURIComponent(window.location.pathname)}`;
        return;
      }
      if (!response.ok) {
        const detail = Object.values(data).flatMap((value) => Array.isArray(value) ? value : [value]).find((value) => typeof value === "string");
        throw new Error(detail || t("operationFailed"));
      }
      productWatch = data;
      showToast(t("watchAdded"));
    }
    productWatchLoaded = true;
    updateProductWatchButton(product);
  } catch (error) {
    showToast(error.message || t("operationFailed"));
    button.disabled = false;
  }
}

function showToast(message) {
  const toast = document.createElement("div");
  toast.className = "toast-message";
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 2800);
}

function reviewStars(value) {
  const rounded = Math.max(0, Math.min(5, Math.round(Number(value) || 0)));
  return `${"★".repeat(rounded)}${"☆".repeat(5 - rounded)}`;
}

function reviewDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString(window.NexoraI18n?.current() === "en" ? "en-US" : "fa-IR");
}

function productRatingSummary(product) {
  if (reviewSummary.loaded) return reviewSummary;
  return {
    average: Number(product.rating_average || 0),
    count: Number(product.rating_count || 0),
  };
}

function updateProductRating(product) {
  const stars = document.querySelector("#product-rating-stars");
  const value = document.querySelector("#product-rating-value");
  const count = document.querySelector("#product-rating-count");
  if (!stars || !value || !count) return;

  const summary = productRatingSummary(product);
  stars.textContent = reviewStars(summary.average);
  stars.setAttribute("aria-label", `${number(summary.average)} / 5`);
  value.textContent = summary.count ? number(summary.average) : "—";
  count.textContent = summary.count
    ? format("reviewCount", { count: number(summary.count) })
    : t("noReviews");
}

function renderReviewSummary(product) {
  const summaryNode = document.querySelector("#review-rating-summary");
  if (!summaryNode) return;

  const summary = productRatingSummary(product);
  const distribution = summary.distribution || {};
  const distributionMarkup = [5, 4, 3, 2, 1].map((rating) => {
    const count = Number(distribution[String(rating)] || 0);
    const width = summary.count ? Math.round((count / summary.count) * 100) : 0;
    return `<div class="review-distribution-row"><span>${escapeHTML(number(rating))} ★</span><span class="review-distribution-track"><i style="width:${width}%"></i></span><b>${escapeHTML(number(count))}</b></div>`;
  }).join("");
  summaryNode.innerHTML = `<div class="review-summary-main"><span class="rating-stars" aria-hidden="true">${summary.count ? reviewStars(summary.average) : "☆☆☆☆☆"}</span><strong>${summary.count ? escapeHTML(number(summary.average)) : "—"}</strong><small>${escapeHTML(summary.count ? format("reviewCount", { count: number(summary.count) }) : t("noReviews"))}</small></div><div class="review-distribution">${distributionMarkup}</div>`;
}

function sortReviewsForDisplay(reviews) {
  return [...reviews].sort((first, second) => {
    if (reviewSort === "highest") return (Number(second.rating || 0) - Number(first.rating || 0)) || (Date.parse(second.created_at || "") - Date.parse(first.created_at || ""));
    if (reviewSort === "helpful") return (Number(second.helpful_count || 0) - Number(first.helpful_count || 0)) || (Number(second.rating || 0) - Number(first.rating || 0));
    return Date.parse(second.created_at || "") - Date.parse(first.created_at || "");
  });
}

function renderReviewsList() {
  const list = document.querySelector("#reviews-list");
  if (!list) return;
  const count = document.querySelector("#reviews-public-count");
  if (count) count.textContent = format("reviewCount", { count: number(productReviews.length) });

  if (!productReviews.length) {
    list.innerHTML = `<div class="empty-inline"><strong>${escapeHTML(t("noReviews"))}</strong><span>${escapeHTML(t("beFirstReview"))}</span></div>`;
    return;
  }

  list.innerHTML = sortReviewsForDisplay(productReviews).map((review) => {
    const title = review.title ? `<h3>${escapeHTML(review.title)}</h3>` : "";
    const helpfulCount = Number(review.helpful_count || 0);
    const helpfulLabel = review.helpful_by_me ? t("helpfulMarked") : t("markHelpful");
    const verifiedBadge = review.is_verified_purchase ? `<span class="verified-purchase"><span aria-hidden="true">✓</span>${escapeHTML(t("verifiedPurchase"))}</span>` : "";
    return `<article class="review-card"><div class="review-card-head"><div><div class="review-author-line"><strong>${escapeHTML(review.customer_name || t("customer"))}</strong>${verifiedBadge}</div><span class="rating-stars" aria-label="${escapeHTML(number(review.rating))} / 5">${reviewStars(review.rating)}</span></div><time datetime="${escapeHTML(review.created_at || "")}">${escapeHTML(reviewDate(review.created_at))}</time></div>${title}<p>${escapeHTML(review.body)}</p><div class="review-card-footer"><button class="review-helpful-button ${review.helpful_by_me ? "is-helpful" : ""}" data-review-helpful="${review.id}" type="button" aria-pressed="${review.helpful_by_me ? "true" : "false"}" title="${escapeHTML(helpfulLabel)}"><span aria-hidden="true">👍</span><span>${escapeHTML(helpfulLabel)}</span><b>${escapeHTML(number(helpfulCount))}</b></button></div></article>`;
  }).join("");
  list.querySelectorAll("[data-review-helpful]").forEach((button) => button.addEventListener("click", () => toggleReviewHelpful(Number(button.dataset.reviewHelpful), button)));
}

function renderQuestionsList() {
  const list = document.querySelector("#questions-list");
  const count = document.querySelector("#questions-count");
  if (!list) return;
  if (count) count.textContent = format("questionCount", { count: number(productQuestions.length) });
  if (!productQuestions.length) {
    list.innerHTML = `<div class="empty-inline"><strong>${escapeHTML(t("noQuestions"))}</strong><span>${escapeHTML(t("productQuestionsHint"))}</span></div>`;
    return;
  }
  list.innerHTML = productQuestions.map((question) => {
    const author = question.customer_name || t("customer");
    const answer = question.answer
      ? `<div class="question-answer"><div class="question-answer-head"><span aria-hidden="true">✦</span><strong>${escapeHTML(t("answeredByNexora"))}</strong><time datetime="${escapeHTML(question.answered_at || "")}">${escapeHTML(reviewDate(question.answered_at))}</time></div><p>${escapeHTML(question.answer)}</p></div>`
      : `<div class="question-pending"><span aria-hidden="true">◷</span><span>${escapeHTML(t("answerPending"))}</span></div>`;
    return `<article class="question-card"><div class="question-card-head"><div class="question-author"><span class="question-avatar" aria-hidden="true">?</span><div><strong>${escapeHTML(author)}</strong><small>${escapeHTML(reviewDate(question.created_at))}</small></div></div><span class="question-card-mark" aria-hidden="true">?</span></div><p class="question-text">${escapeHTML(question.question)}</p>${answer}</article>`;
  }).join("");
}

function renderQuestionComposer() {
  const composer = document.querySelector("#question-composer");
  if (!composer) return;
  if (!questionUser) {
    const loginUrl = `/account/?next=${encodeURIComponent(window.location.pathname)}`;
    composer.innerHTML = `<div class="question-login-callout"><span class="question-login-icon" aria-hidden="true">?</span><div><strong>${escapeHTML(t("askQuestion"))}</strong><p>${escapeHTML(t("loginToAsk"))}</p></div><a class="secondary-button" href="${loginUrl}">${escapeHTML(t("login"))}</a></div>`;
    return;
  }
  const displayName = escapeHTML(questionUser.first_name || questionUser.username || t("customer"));
  composer.innerHTML = `<form class="question-form" id="question-form"><div class="question-form-header"><div><strong>${escapeHTML(t("askQuestion"))}</strong><small>${displayName}</small></div><span aria-hidden="true">?</span></div><label><span>${escapeHTML(t("questionFieldLabel"))}</span><textarea name="question" maxlength="1000" rows="5" required placeholder="${escapeHTML(t("questionPlaceholder"))}"></textarea></label><div class="question-form-actions"><button class="primary-button" type="submit"><span aria-hidden="true">↗</span>${escapeHTML(t("submitQuestion"))}</button><small id="question-form-message" role="status"></small></div></form>`;
  composer.querySelector("#question-form")?.addEventListener("submit", submitQuestion);
}

function renderQuestionSection() {
  renderQuestionsList();
  renderQuestionComposer();
}

async function loadQuestions() {
  const section = document.querySelector("#product-questions");
  if (!section) return;
  section.hidden = false;
  try {
    const [data, user] = await Promise.all([
      getJSON(`products/${encodeURIComponent(slug)}/questions/`),
      loadReviewUser(),
    ]);
    productQuestions = Array.isArray(data.results) ? data.results : [];
    questionUser = user;
    renderQuestionSection();
  } catch (error) {
    const list = document.querySelector("#questions-list");
    if (list) list.innerHTML = `<div class="empty-inline">${escapeHTML(t("questionLoadFailed"))}</div>`;
    renderQuestionComposer();
  }
}

async function submitQuestion(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector("button[type=submit]");
  const message = form.querySelector("#question-form-message");
  message.textContent = "";
  if (!form.reportValidity()) return;
  button.disabled = true;
  try {
    const response = await fetch(`${API_BASE}products/${encodeURIComponent(slug)}/questions/`, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": await csrf() },
      body: JSON.stringify({ question: form.question.value.trim() }),
    });
    const data = await response.json().catch(() => ({}));
    if (response.status === 401) {
      window.location.href = `/account/?next=${encodeURIComponent(window.location.pathname)}`;
      return;
    }
    if (!response.ok) {
      const errors = Object.values(data).flatMap((value) => Array.isArray(value) ? value : [value]).filter((value) => typeof value === "string").join(" ");
      throw new Error(errors || t("questionSubmitFailed"));
    }
    if (data.question) productQuestions = [data.question, ...productQuestions];
    renderQuestionSection();
    showToast(t("questionSaved"));
  } catch (error) {
    message.textContent = error.message || t("questionSubmitFailed");
  } finally {
    button.disabled = false;
  }
}

async function toggleReviewHelpful(reviewId, button) {
  if (!reviewUser) {
    window.location.href = `/account/?next=${encodeURIComponent(window.location.pathname)}`;
    return;
  }
  button.disabled = true;
  try {
    const response = await fetch(`${API_BASE}products/${encodeURIComponent(slug)}/reviews/${reviewId}/helpful/`, {
      method: "POST",
      credentials: "same-origin",
      headers: { "X-CSRFToken": await csrf() },
    });
    const data = await response.json().catch(() => ({}));
    if (response.status === 401) {
      window.location.href = `/account/?next=${encodeURIComponent(window.location.pathname)}`;
      return;
    }
    if (!response.ok) throw new Error(data.detail || t("helpfulVoteFailed"));
    const review = productReviews.find((item) => Number(item.id) === reviewId);
    if (review) {
      review.helpful_count = Number(data.helpful_count || 0);
      review.helpful_by_me = Boolean(data.helpful);
    }
    renderReviewsList();
    showToast(t(data.helpful ? "helpfulMarkedToast" : "helpfulUnmarkedToast"));
  } catch (error) {
    showToast(error.message || t("helpfulVoteFailed"));
    button.disabled = false;
  }
}

function renderReviewComposer() {
  const composer = document.querySelector("#review-composer");
  if (!composer) return;

  if (!reviewUser) {
    const loginUrl = `/account/?next=${encodeURIComponent(window.location.pathname)}`;
    composer.innerHTML = `<div class="review-login-callout"><span class="review-login-icon" aria-hidden="true">✎</span><div><strong>${escapeHTML(t("reviewGuestTitle"))}</strong><p>${escapeHTML(t("reviewGuestHint"))}</p></div><a class="secondary-button" href="${loginUrl}">${escapeHTML(t("login"))}</a></div>`;
    return;
  }

  const existingReview = productReviews.find((review) => review.is_mine);
  const ratingLabels = {
    5: "ratingExcellent",
    4: "ratingGood",
    3: "ratingAverage",
    2: "ratingWeak",
    1: "ratingBad",
  };
  const options = [5, 4, 3, 2, 1].map((rating) => `<option value="${rating}" ${Number(existingReview?.rating) === rating ? "selected" : ""}>${rating} — ${escapeHTML(t(ratingLabels[rating]))}</option>`).join("");
  const titleValue = escapeHTML(existingReview?.title || "");
  const bodyValue = escapeHTML(existingReview?.body || "");
  const displayName = escapeHTML(reviewUser.first_name || reviewUser.username || t("customer"));

  composer.innerHTML = `<form class="review-form" id="review-form"><div class="review-form-header"><strong>${escapeHTML(existingReview ? t("updateReview") : t("submitReview"))}</strong><small>${displayName}</small></div><div class="form-grid"><label>${escapeHTML(t("rating"))}<select name="rating" required>${options}</select></label><label>${escapeHTML(t("reviewTitleLabel"))}<input name="title" maxlength="120" value="${titleValue}" placeholder="${escapeHTML(t("reviewTitlePlaceholder"))}"></label><label>${escapeHTML(t("reviewBodyLabel"))}<textarea name="body" maxlength="1500" rows="5" required placeholder="${escapeHTML(t("reviewBodyPlaceholder"))}">${bodyValue}</textarea></label></div><div class="review-form-actions"><button class="primary-button" type="submit">${escapeHTML(existingReview ? t("updateReview") : t("submitReview"))}</button><small class="review-form-message" id="review-form-message" role="status"></small></div></form>`;
  composer.querySelector("#review-form")?.addEventListener("submit", submitReview);
}

function renderReviewSection(product) {
  renderReviewSummary(product);
  updateProductRating(product);
  renderReviewsList();
  renderReviewComposer();
}

async function loadReviewUser() {
  try {
    const response = await fetch(`${API_BASE}auth/profile/`, { credentials: "same-origin" });
    if (!response.ok) return null;
    return response.json();
  } catch (error) {
    return null;
  }
}

function apiPathFromUrl(url) {
  const parsed = new URL(url, window.location.origin);
  const apiPrefix = new URL(API_BASE, window.location.origin).pathname;
  return (parsed.pathname.startsWith(apiPrefix) ? parsed.pathname.slice(apiPrefix.length) : parsed.pathname.replace(/^\/+/, "")) + parsed.search;
}

async function collectReviewPages(firstPage) {
  const reviews = Array.isArray(firstPage) ? [...firstPage] : [...(firstPage.results || [])];
  let nextUrl = firstPage?.next || null;
  let pageCount = 1;
  while (nextUrl && pageCount < 100) {
    const page = await getJSON(apiPathFromUrl(nextUrl));
    if (Array.isArray(page)) reviews.push(...page);
    else reviews.push(...(Array.isArray(page.results) ? page.results : []));
    nextUrl = page?.next || null;
    pageCount += 1;
  }
  return reviews;
}

async function loadReviews(product) {
  const section = document.querySelector("#product-reviews");
  if (!section) return;
  section.hidden = false;

  try {
    const [data, user] = await Promise.all([
      getJSON(`products/${encodeURIComponent(slug)}/reviews/?sort=${encodeURIComponent(reviewSort)}`),
      loadReviewUser(),
    ]);
    productReviews = await collectReviewPages(data);
    reviewSummary = {
      average: Number(data.average || 0),
      count: Number(data.count || 0),
      distribution: data.rating_distribution || {},
      loaded: true,
    };
    reviewUser = user;
    questionUser = user;
    renderReviewSection(product);
  } catch (error) {
    reviewUser = null;
    renderReviewComposer();
    const list = document.querySelector("#reviews-list");
    if (list) list.innerHTML = `<div class="empty-inline">${escapeHTML(t("reviewLoadFailed"))}</div>`;
  }
}

async function submitReview(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector("button[type=submit]");
  const message = form.querySelector("#review-form-message");
  message.textContent = "";
  if (!form.reportValidity()) return;

  button.disabled = true;
  const wasUpdating = productReviews.some((review) => review.is_mine);
  try {
    const response = await fetch(`${API_BASE}products/${encodeURIComponent(slug)}/reviews/`, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": await csrf(),
      },
      body: JSON.stringify({
        rating: Number(form.rating.value),
        title: form.title.value.trim(),
        body: form.body.value.trim(),
      }),
    });
    const data = await response.json().catch(() => ({}));
    if (response.status === 401) {
      window.location.href = `/account/?next=${encodeURIComponent(window.location.pathname)}`;
      return;
    }
    if (!response.ok) {
      const errors = Object.values(data)
        .flatMap((value) => Array.isArray(value) ? value : [value])
        .filter((value) => typeof value === "string")
        .join(" ");
      throw new Error(errors || t("reviewSubmitFailed"));
    }

    const savedReview = data.review;
    const existingIndex = productReviews.findIndex((review) => review.is_mine);
    if (existingIndex >= 0) productReviews[existingIndex] = savedReview;
    else productReviews = [savedReview, ...productReviews];
    reviewSummary = {
      average: Number(data.average || 0),
      count: Number(data.count || 0),
      distribution: data.rating_distribution || {},
      loaded: true,
    };
    renderReviewSection(window.productDetail);
    showToast(t(wasUpdating ? "reviewUpdated" : "reviewSaved"));
  } catch (error) {
    message.textContent = error.message || t("reviewSubmitFailed");
  } finally {
    button.disabled = false;
  }
}

function renderProduct(product) {
  const specs = Object.entries(product.specifications || {});
  const displayName = window.NexoraI18n?.productName(product) || product.name;
  const displayCategory = window.NexoraI18n?.category(product.category?.slug, product.category?.name || t("digitalAccessories")) || t("digitalAccessories");
  const displayDescription = window.NexoraI18n?.productDescription(product) || product.description || t("carefulChoiceText");
  const image = product.image_url ? `<img class="product-detail-image" src="${escapeHTML(product.image_url)}" alt="${escapeHTML(displayName)}">` : `<div class="product-detail-placeholder"><span>${escapeHTML((product.brand || "N").slice(0, 1))}</span></div>`;
  const specsMarkup = specs.length ? `<dl>${specs.map(([key, value]) => `<div><dt>${escapeHTML(key)}</dt><dd>${escapeHTML(Array.isArray(value) ? value.join(", ") : value === true ? t("yes") : value === false ? t("no") : value)}</dd></div>`).join("")}</dl>` : `<p class="empty-inline">${escapeHTML(t("carefulChoiceText"))}</p>`;
  const detailDiscount = Number(product.discount_amount || 0);
  const detailDiscountLabel = detailDiscount > 0 ? `<small class="detail-discount-label">${escapeHTML(recommendationDiscountLabel(product))}</small>` : "";
  const detailPrice = `<div class="product-detail-price"><div class="price-stack"><strong>${escapeHTML(money(product.final_price))}</strong>${detailDiscount > 0 ? `<del>${escapeHTML(money(product.price))}</del>${detailDiscountLabel}<small class="product-savings"><span aria-hidden="true">✦</span>${escapeHTML(format("youSave", { amount: money(detailDiscount) }))}</small>${discountCountdownMarkup(product)}` : ""}</div></div>`;
  document.querySelector("#product-detail-content").innerHTML = `<div class="product-detail-visual">${image}${detailDiscount > 0 ? `<span class="detail-discount-mark">✦ ${escapeHTML(t("specialOffer"))}</span>` : ""}<span class="detail-badge">${escapeHTML(displayCategory)}</span></div><div class="product-detail-copy"><p class="eyebrow"><span></span><span data-i18n="productDetails">${escapeHTML(t("productDetails"))}</span></p><h1>${escapeHTML(displayName)}</h1><p class="product-detail-brand">${escapeHTML(product.brand || "Nexora")} · ${escapeHTML(t("sku"))}: ${escapeHTML(product.sku)}</p><div class="product-rating-inline"><span class="rating-stars" id="product-rating-stars" aria-hidden="true">☆☆☆☆☆</span><strong id="product-rating-value">—</strong><span id="product-rating-count"></span></div><p class="product-detail-description">${escapeHTML(displayDescription)}</p>${detailPrice}<p class="product-stock ${product.is_in_stock ? "in-stock" : "out-of-stock"}">${product.is_in_stock ? escapeHTML(format("stockCount", { count: number(product.stock_quantity) })) : escapeHTML(t("unavailable"))}</p><button class="primary-button detail-add" type="button" ${product.is_in_stock ? "" : "disabled"}><span class="button-icon" aria-hidden="true">🛒</span><span>${escapeHTML(product.is_in_stock ? t("addToCart") : t("unavailable"))}</span><span>←</span></button><div class="specification-panel"><h2>${escapeHTML(t("specifications"))}</h2>${specsMarkup}</div></div>`;
  const detailContent = document.querySelector("#product-detail-content");
  const addButton = detailContent.querySelector(".detail-add");
  const actionRow = document.createElement("div");
  actionRow.className = "detail-actions";
  const watchButton = document.createElement("button");
  watchButton.className = "secondary-button watch-button";
  watchButton.id = "product-watch-button";
  watchButton.type = "button";
  watchButton.setAttribute("aria-pressed", "false");
  watchButton.innerHTML = `<span class="button-icon" aria-hidden="true">◉</span><span data-watch-label>${escapeHTML(t("watchLoading"))}</span>`;
  if (addButton?.parentNode) {
    addButton.parentNode.insertBefore(actionRow, addButton);
    actionRow.appendChild(addButton);
    actionRow.appendChild(watchButton);
    const watchHint = document.createElement("p");
    watchHint.className = "watch-hint";
    watchHint.id = "product-watch-hint";
    watchHint.textContent = t("watchHint");
    actionRow.insertAdjacentElement("afterend", watchHint);
  }
  const favoriteButton = document.createElement("button");
  favoriteButton.className = "heart-button detail-heart";
  favoriteButton.dataset.favoriteProduct = product.id;
  favoriteButton.type = "button";
  favoriteButton.setAttribute("aria-label", t("addToFavorites"));
  favoriteButton.setAttribute("aria-pressed", "false");
  favoriteButton.textContent = "♡";
  detailContent.querySelector(".product-detail-visual")?.appendChild(favoriteButton);
  window.NexoraFavorites?.bindButtons(detailContent);
  detailContent.querySelector(".detail-badge").textContent = displayCategory;
  detailContent.querySelector(".product-detail-description").textContent = displayDescription;
  detailContent.querySelectorAll(".specification-panel dt").forEach((element, index) => { element.textContent = window.NexoraI18n?.specificationLabel(specs[index][0]) || specs[index][0]; });
  detailContent.querySelectorAll(".specification-panel dd").forEach((element, index) => { const value = specs[index][1]; element.textContent = Array.isArray(value) ? value.join(", ") : value === true ? t("yes") : value === false ? t("no") : value; });
  updateProductRating(product);
  updateDiscountCountdowns();
  document.querySelector(".detail-add")?.addEventListener("click", async (event) => { event.currentTarget.disabled = true; try { await addToCart(product); } catch (error) { showToast(error.message); } finally { event.currentTarget.disabled = false; } });
  document.querySelector("#product-watch-button")?.addEventListener("click", () => toggleProductWatch(product));
  updateProductWatchButton(product);
}

async function loadProduct() {
  try {
    const product = await getJSON(`products/${encodeURIComponent(slug)}/`);
    window.productDetail = product;
    rememberProduct(product);
    await window.NexoraFavorites?.load();
    renderProduct(product);
    document.querySelector("#product-detail-state").hidden = true;
    document.querySelector("#product-detail-content").hidden = false;
    document.querySelector("#product-reviews").hidden = false;
    document.querySelector("#product-questions").hidden = false;
    renderReviewSection(product);
    loadProductWatch(product);
    loadReviews(product);
    loadQuestions(product);
    loadRecommendations(product);
    document.title = `${window.NexoraI18n?.productName(product) || product.name} | Nexora`;
    return product;
  } catch (error) {
    document.querySelector("#product-detail-state").innerHTML = `<span class="state-icon">!</span><h3>${t("noProducts")}</h3><p>${t("changeFilter")}</p>`;
  }
}

function updateThemeButton() { document.querySelector("#theme-toggle").textContent = document.documentElement.classList.contains("dark") ? "☼" : "☾"; }
document.querySelector("#theme-toggle").addEventListener("click", () => { document.documentElement.classList.toggle("dark"); localStorage.setItem("nexora-theme", document.documentElement.classList.contains("dark") ? "dark" : "light"); updateThemeButton(); });
document.querySelector("#review-sort")?.addEventListener("change", (event) => { reviewSort = event.target.value; if (window.productDetail) loadReviews(window.productDetail); });
if (localStorage.getItem("nexora-theme") === "dark") document.documentElement.classList.add("dark");
updateThemeButton();
window.setInterval(updateDiscountCountdowns, 1000);
window.addEventListener("nexora-language-changed", () => { if (window.productDetail) { renderProduct(window.productDetail); renderReviewSection(window.productDetail); renderQuestionSection(); renderRecommendations(); updateDiscountCountdowns(); } });
loadProduct();
