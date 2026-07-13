// Shared between login.js and signup.js: email validation, inline field errors,
// and a page-level success/error banner (used instead of native alert()).

function validateEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

function showError(input, message) {
  input.classList.add("input-error");
  input.setAttribute("aria-invalid", "true");
  const existingError = input.parentNode.querySelector(".error-message");
  if (existingError) existingError.remove();

  const errorId = `${input.id || input.name}-error`;
  const errorDiv = document.createElement("div");
  errorDiv.id = errorId;
  errorDiv.className = "error-message";
  errorDiv.setAttribute("role", "alert");
  errorDiv.textContent = message;
  input.parentNode.appendChild(errorDiv);
  input.setAttribute("aria-describedby", errorId);
}

function clearError(input) {
  input.classList.remove("input-error");
  input.removeAttribute("aria-invalid");
  input.removeAttribute("aria-describedby");
  const errorMessage = input.parentNode.querySelector(".error-message");
  if (errorMessage) errorMessage.remove();
}

function showFormAlert(message, type) {
  const el = document.getElementById("formAlert");
  if (!el) return;
  el.textContent = message;
  el.className = `form-alert form-alert-${type}`;
  el.hidden = false;
  el.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function clearFormAlert() {
  const el = document.getElementById("formAlert");
  if (!el) return;
  el.hidden = true;
  el.textContent = "";
}
