const FEEDBACK_API_BASE = "/api/v1/";
const FEEDBACK_STORAGE_KEY = "nexora-feedback-submitted";
const feedbackText = (key) => window.NexoraI18n?.t(key) || key;
let feedbackItems = [];
let feedbackLoaded = false;

function feedbackEscape(value) {
  return String(value ?? "").replace(/[&<>\'\"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character]));
}

function feedbackNumber(value) {
  const locale = document.documentElement.lang === "en" ? "en-US" : "fa-IR";
  return new Intl.NumberFormat(locale).format(value);
}

function feedbackDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString(document.documentElement.lang === "en" ? "en-US" : "fa-IR", { year: "numeric", month: "short", day: "numeric" });
}

function renderFeedbackSummary() {
  const summary = document.querySelector("#feedback-summary");
  if (!summary) return;
  if (!feedbackItems.length) {
    summary.textContent = "";
    return;
  }
  const average = feedbackItems.reduce((total, item) => total + Number(item.rating || 0), 0) / feedbackItems.length;
  summary.textContent = `★ ${feedbackNumber(average.toFixed(1))} · ${feedbackNumber(feedbackItems.length)} ${feedbackText("feedbackReviewCount")}`;
}

function renderFeedbackList() {
  const list = document.querySelector("#feedback-list");
  if (!list) return;
  renderFeedbackSummary();
  if (!feedbackItems.length) {
    list.innerHTML = `<div class="feedback-list-state"><span class="feedback-empty-icon" aria-hidden="true">✦</span><p>${feedbackEscape(feedbackText("feedbackNoReviews"))}</p></div>`;
    return;
  }
  list.innerHTML = feedbackItems.map((item) => {
    const rating = Math.max(0, Math.min(5, Number(item.rating || 0)));
    const stars = "★".repeat(rating) + "☆".repeat(5 - rating);
    const name = item.customer_name?.trim() || feedbackText("feedbackGuest");
    const comment = item.comment?.trim() || feedbackText("feedbackNoComment");
    return `<article class="feedback-card"><div class="feedback-card-head"><div class="feedback-author"><span class="feedback-avatar" aria-hidden="true">${feedbackEscape(name.slice(0, 1).toUpperCase())}</span><div><strong>${feedbackEscape(name)}</strong><small>${feedbackEscape(feedbackDate(item.created_at))}</small></div></div><span class="feedback-stars" aria-label="${feedbackEscape(feedbackNumber(rating))}">${stars}</span></div><p>${feedbackEscape(comment)}</p></article>`;
  }).join("");
}

function renderFeedbackError() {
  const list = document.querySelector("#feedback-list");
  if (!list) return;
  list.innerHTML = `<div class="feedback-list-state"><span class="feedback-empty-icon" aria-hidden="true">!</span><p>${feedbackEscape(feedbackText("feedbackLoadFailed"))}</p></div>`;
}

async function loadFeedback() {
  const list = document.querySelector("#feedback-list");
  if (!list) return;
  try {
    let nextUrl = `${FEEDBACK_API_BASE}auth/feedback/?page_path=${encodeURIComponent("/")}`;
    const items = [];
    let pageCount = 0;

    while (nextUrl && pageCount < 100) {
      const response = await fetch(nextUrl, { credentials: "same-origin", cache: "no-store" });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error("feedback-request-failed");

      if (Array.isArray(data)) {
        items.push(...data);
        nextUrl = null;
      } else {
        items.push(...(Array.isArray(data.results) ? data.results : []));
        if (!data.next) {
          nextUrl = null;
        } else {
          const next = new URL(data.next, window.location.origin);
          nextUrl = next.pathname + next.search;
        }
      }
      pageCount += 1;
    }

    feedbackItems = items;
    feedbackLoaded = true;
    renderFeedbackList();
  } catch (error) {
    feedbackLoaded = true;
    renderFeedbackError();
  }
}

function feedbackCookie(name) {
  const cookie = document.cookie.split("; ").find((item) => item.startsWith(`${name}=`));
  return cookie ? decodeURIComponent(cookie.slice(name.length + 1)) : null;
}

async function feedbackCSRF() {
  if (feedbackCookie("csrftoken")) return feedbackCookie("csrftoken");
  const response = await fetch(`${FEEDBACK_API_BASE}auth/csrf/`, { credentials: "same-origin" });
  if (!response.ok || !feedbackCookie("csrftoken")) throw new Error(feedbackText("feedbackError"));
  return feedbackCookie("csrftoken");
}

function feedbackWasSubmitted() {
  try {
    return localStorage.getItem(FEEDBACK_STORAGE_KEY) === "1";
  } catch (error) {
    return false;
  }
}

function setFeedbackMessage(key) {
  const message = document.querySelector("#feedback-message");
  if (!message) return;
  message.dataset.feedbackState = key;
  message.textContent = feedbackText(key);
}

function lockFeedbackForm() {
  const form = document.querySelector("#feedback-form");
  if (!form) return;
  form.classList.add("is-submitted");
  form.querySelectorAll("input, textarea, button").forEach((element) => { element.disabled = true; });
  setFeedbackMessage("feedbackThanks");
}

async function submitFeedback(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const submit = form.querySelector("button[type=submit]");
  if (!form.reportValidity()) return;

  submit.disabled = true;
  setFeedbackMessage("");
  try {
    const response = await fetch(`${FEEDBACK_API_BASE}auth/feedback/`, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": await feedbackCSRF(),
      },
      body: JSON.stringify({
        rating: Number(form.rating.value),
        comment: form.comment.value.trim(),
        page: window.location.pathname,
      }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const errors = Object.values(data)
        .flatMap((value) => Array.isArray(value) ? value : [value])
        .filter((value) => typeof value === "string")
        .join(" ");
      throw new Error(errors || feedbackText("feedbackError"));
    }
    if (data?.id) {
      feedbackItems = [data, ...feedbackItems.filter((item) => Number(item.id) !== Number(data.id))];
      feedbackLoaded = true;
      renderFeedbackList();
    }
    try { localStorage.setItem(FEEDBACK_STORAGE_KEY, "1"); } catch (error) { /* best effort */ }
    lockFeedbackForm();
    await loadFeedback();
  } catch (error) {
    setFeedbackMessage("feedbackError");
    submit.disabled = false;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("#feedback-form");
  if (form) {
    if (feedbackWasSubmitted()) lockFeedbackForm();
    form.addEventListener("submit", submitFeedback);
  }
  loadFeedback();
});

window.addEventListener("nexora-language-changed", () => {
  const message = document.querySelector("#feedback-message");
  if (message?.dataset.feedbackState) setFeedbackMessage(message.dataset.feedbackState);
  if (feedbackLoaded) renderFeedbackList();
});
