const loginForm = document.getElementById('loginForm');
const submitButton = document.getElementById('submitButton');
const passwordToggle = document.getElementById('passwordToggle');
const passwordInput = document.getElementById('password');
const toggleIcon = document.getElementById('toggleIcon');
const emailInput = document.getElementById('email');
const forgotPassword = document.getElementById('forgotPassword');

passwordToggle.addEventListener('click', () => {
  const type = passwordInput.type === 'password' ? 'text' : 'password';
  passwordInput.type = type;
  toggleIcon.textContent = type === 'password' ? '👁️' : '🙈';
});

function validateEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

function validatePassword(password) {
  return password.length >= 6;
}

function showError(input, message) {
  input.style.borderColor = 'var(--error)';
  input.style.boxShadow = '0 0 0 3px rgba(239, 68, 68, 0.1)';
  const existingError = input.parentNode.querySelector('.error-message');
  if (existingError) existingError.remove();

  const errorDiv = document.createElement('div');
  errorDiv.className = 'error-message';
  errorDiv.style.cssText = 'color: var(--error); font-size: 0.8rem; margin-top: 0.25rem;';
  errorDiv.textContent = message;
  input.parentNode.appendChild(errorDiv);
}

function clearError(input) {
  input.style.borderColor = 'var(--border)';
  input.style.boxShadow = 'none';
  const error = input.parentNode.querySelector('.error-message');
  if (error) error.remove();
}

emailInput.addEventListener('blur', () => {
  if (emailInput.value && !validateEmail(emailInput.value)) {
    showError(emailInput, 'Please enter a valid email address');
  } else {
    clearError(emailInput);
  }
});

passwordInput.addEventListener('blur', () => {
  if (passwordInput.value && !validatePassword(passwordInput.value)) {
    showError(passwordInput, 'Password must be at least 6 characters');
  } else {
    clearError(passwordInput);
  }
});

loginForm.addEventListener('submit', function (e) {
  e.preventDefault();

  clearError(emailInput);
  clearError(passwordInput);
  let isValid = true;

  if (!validateEmail(emailInput.value)) {
    showError(emailInput, 'Please enter a valid email address');
    isValid = false;
  }
  if (!validatePassword(passwordInput.value)) {
    showError(passwordInput, 'Password must be at least 6 characters');
    isValid = false;
  }

  if (isValid) {
    submitButton.classList.add('loading');

    fetch("/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        email: emailInput.value,
        password: passwordInput.value
      })
    })
    .then(response => response.json())
    .then(data => {
      submitButton.classList.remove('loading');
      if (data.success) {
        alert("Login successful!");
        window.location.href = "/dashboard";
      } else {
        alert("Invalid credentials!");
      }
    })
    .catch(error => {
      submitButton.classList.remove('loading');
      alert("An error occurred. Please try again.");
    });
  }
});

forgotPassword.addEventListener('click', e => {
  e.preventDefault();
  alert('Forgot password functionality would be implemented here');
});

document.addEventListener('keydown', function (e) {
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
    loginForm.dispatchEvent(new Event('submit'));
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
    loginForm.dispatchEvent(new Event('submit'));
  }
});
