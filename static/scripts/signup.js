document.addEventListener("DOMContentLoaded", function () {
  // ===== DOM ELEMENTS =====
  const signupForm = document.getElementById('signupForm');
  const submitButton = document.getElementById('submitButton');
  const usernameInput = document.getElementById('username');
  const emailInput = document.getElementById('email');
  const passwordInput = document.getElementById('password');
  const confirmPasswordInput = document.getElementById('confirmPassword');
  const passwordToggle = document.getElementById('passwordToggle');
  const toggleIcon = document.getElementById('toggleIcon');
  const confirmPasswordToggle = document.getElementById('confirmPasswordToggle');
  const confirmToggleIcon = document.getElementById('confirmToggleIcon');

  function togglePasswordVisibility(inputElement, iconElement) {
    const type = inputElement.type === 'password' ? 'text' : 'password';
    inputElement.type = type;
    iconElement.textContent = type === 'password' ? '👁️' : '🙈';
  }

  passwordToggle.addEventListener('click', () => togglePasswordVisibility(passwordInput, toggleIcon));
  confirmPasswordToggle.addEventListener('click', () => togglePasswordVisibility(confirmPasswordInput, confirmToggleIcon));

  function validateUsername(username) {
    return username.length >= 3;
  }

  function validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }

  function validatePassword(password) {
    const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{6,}$/;
    return passwordRegex.test(password);
  }

  function showError(input, message) {
    input.style.borderColor = 'var(--error)';
    input.style.boxShadow = '0 0 0 3px rgba(239, 68, 68, 0.1)';
    const existingError = input.parentNode.querySelector('.error-message');
    if (existingError) existingError.remove();
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    input.parentNode.appendChild(errorDiv);
  }

  function clearError(input) {
    input.style.borderColor = 'var(--border)';
    input.style.boxShadow = 'none';
    const errorMessage = input.parentNode.querySelector('.error-message');
    if (errorMessage) errorMessage.remove();
  }

  signupForm.addEventListener('submit', function (e) {
    e.preventDefault();
    clearError(usernameInput);
    clearError(emailInput);
    clearError(passwordInput);
    clearError(confirmPasswordInput);

    let isValid = true;

    if (!validateUsername(usernameInput.value)) {
      showError(usernameInput, 'Username must be at least 3 characters');
      isValid = false;
    }

    if (!validateEmail(emailInput.value)) {
      showError(emailInput, 'Please enter a valid email address');
      isValid = false;
    }

    if (!validatePassword(passwordInput.value)) {
      showError(passwordInput, 'Password needs 6+ chars, 1 uppercase, 1 lowercase, 1 number');
      isValid = false;
    }

    if (confirmPasswordInput.value !== passwordInput.value) {
      showError(confirmPasswordInput, 'Passwords do not match');
      isValid = false;
    } else if (!confirmPasswordInput.value) {
      showError(confirmPasswordInput, 'Please confirm your password');
      isValid = false;
    }

    if (isValid) {
      submitButton.classList.add('loading');
      fetch("/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: usernameInput.value,
          email: emailInput.value,
          password: passwordInput.value
        })
      })
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            window.location.href = data.redirect_url;
          } else {
            alert(data.message || "Signup failed. Try again.");
            submitButton.classList.remove('loading');
          }
        })
        .catch(error => {
          console.error("Signup error:", error);
          alert("Something went wrong. Try again.");
          submitButton.classList.remove('loading');
        });
    }
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      signupForm.dispatchEvent(new Event('submit'));
    }
  });

  usernameInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      emailInput.focus();
    }
  });

  emailInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      passwordInput.focus();
    }
  });

  passwordInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      confirmPasswordInput.focus();
    }
  });

  confirmPasswordInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      signupForm.dispatchEvent(new Event('submit'));
    }
  });
});
