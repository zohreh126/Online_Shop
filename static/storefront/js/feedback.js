const FEEDBACK_API_BASE = "/api/v1/";
const FEEDBACK_STORAGE_KEY = "nexora-feedback-submitted";
const feedbackText = (key) => window.NexoraI18n?.t(key) || key;

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
    try { localStorage.setItem(FEEDBACK_STORAGE_KEY, "1"); } catch (error) { /* best effort */ }
    lockFeedbackForm();
  } catch (error) {
    setFeedbackMessage("feedbackError");
    submit.disabled = false;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("#feedback-form");
  if (!form) return;
  if (feedbackWasSubmitted()) lockFeedbackForm();
  form.addEventListener("submit", submitFeedback);
});

window.addEventListener("nexora-language-changed", () => {
  const message = document.querySelector("#feedback-message");
  if (message?.dataset.feedbackState) setFeedbackMessage(message.dataset.feedbackState);
});
