document.addEventListener("DOMContentLoaded", function () {
  // ===== DOM ELEMENTS =====
  const signupForm = document.getElementById("signupForm");
  const submitButton = document.getElementById("submitButton");
  const usernameInput = document.getElementById("username");
  const emailInput = document.getElementById("email");
  const passwordInput = document.getElementById("password");
  const confirmPasswordInput = document.getElementById("confirmPassword");
  const passwordToggle = document.getElementById("passwordToggle");
  const toggleIcon = document.getElementById("toggleIcon");
  const confirmPasswordToggle = document.getElementById(
    "confirmPasswordToggle",
  );
  const confirmToggleIcon = document.getElementById("confirmToggleIcon");
  const firstNameInput = document.getElementById("firstName");
  const lastNameInput = document.getElementById("lastName");
  const CSRF_TOKEN = document.querySelector('meta[name="csrf-token"]').content;

  function togglePasswordVisibility(inputElement, iconElement) {
    const type = inputElement.type === "password" ? "text" : "password";
    inputElement.type = type;
    iconElement.textContent = type === "password" ? "👁️" : "🙈";
  }

  passwordToggle.addEventListener("click", () =>
    togglePasswordVisibility(passwordInput, toggleIcon),
  );
  confirmPasswordToggle.addEventListener("click", () =>
    togglePasswordVisibility(confirmPasswordInput, confirmToggleIcon),
  );

  function validateUsername(username) {
    return username.length >= 3;
  }

  function validatePassword(password) {
    const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{6,}$/;
    return passwordRegex.test(password);
  }

  signupForm.addEventListener("submit", function (e) {
    e.preventDefault();
    clearError(usernameInput);
    clearError(emailInput);
    clearError(passwordInput);
    clearError(confirmPasswordInput);
    clearError(firstNameInput);
    clearError(lastNameInput);
    clearFormAlert();

    let isValid = true;

    if (!firstNameInput.value.trim()) {
      showError(firstNameInput, I18N.firstNameRequired);
      isValid = false;
    }
    if (!lastNameInput.value.trim()) {
      showError(lastNameInput, I18N.lastNameRequired);
      isValid = false;
    }

    if (!validateUsername(usernameInput.value)) {
      showError(usernameInput, I18N.usernameTooShort);
      isValid = false;
    }

    if (!validateEmail(emailInput.value)) {
      showError(emailInput, I18N.invalidEmail);
      isValid = false;
    }

    if (!validatePassword(passwordInput.value)) {
      showError(
        passwordInput,
        I18N.weakPassword,
      );
      isValid = false;
    }

    if (confirmPasswordInput.value !== passwordInput.value) {
      showError(confirmPasswordInput, I18N.passwordsDontMatch);
      isValid = false;
    } else if (!confirmPasswordInput.value) {
      showError(confirmPasswordInput, I18N.confirmPasswordRequired);
      isValid = false;
    }

    if (isValid) {
      submitButton.classList.add("loading");
      fetch("/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": CSRF_TOKEN },
        body: JSON.stringify({
          firstName: firstNameInput.value.trim(),
          lastName: lastNameInput.value.trim(),
          username: usernameInput.value.trim(),
          email: emailInput.value.trim(),
          password: passwordInput.value,
        }),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            window.location.href = data.redirect_url;
          } else {
            showFormAlert(data.message || I18N.signupFailed, "error");
            submitButton.classList.remove("loading");
          }
        })
        .catch((error) => {
          console.error("Signup error:", error);
          showFormAlert(I18N.somethingWentWrong, "error");
          submitButton.classList.remove("loading");
        });
    }
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      signupForm.dispatchEvent(new Event("submit"));
    }
  });

  usernameInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      e.preventDefault();
      emailInput.focus();
    }
  });

  emailInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      e.preventDefault();
      passwordInput.focus();
    }
  });

  passwordInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      e.preventDefault();
      confirmPasswordInput.focus();
    }
  });

  confirmPasswordInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      e.preventDefault();
      signupForm.dispatchEvent(new Event("submit"));
    }
  });
});
