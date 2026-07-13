const loginForm = document.getElementById('loginForm');
const submitButton = document.getElementById('submitButton');
const passwordToggle = document.getElementById('passwordToggle');
const passwordInput = document.getElementById('password');
const toggleIcon = document.getElementById('toggleIcon');
const emailInput = document.getElementById('email');
const forgotPassword = document.getElementById('forgotPassword');
const CSRF_TOKEN = document.querySelector('meta[name="csrf-token"]').content;

window.FP_CONFIG = {
  openModal: () => { document.getElementById('fpModal').style.display = 'flex'; },
  closeModal: () => { document.getElementById('fpModal').style.display = 'none'; },
  onResetSuccess: (message) => { showFormAlert(message + I18N.canNowLogin, 'success'); },
};

passwordToggle.addEventListener('click', () => {
  const type = passwordInput.type === 'password' ? 'text' : 'password';
  passwordInput.type = type;
  toggleIcon.textContent = type === 'password' ? '👁️' : '🙈';
});

function validatePassword(password) {
  return password.length >= 6;
}

emailInput.addEventListener('blur', () => {
  if (emailInput.value && !validateEmail(emailInput.value)) {
    showError(emailInput, I18N.invalidEmail);
  } else {
    clearError(emailInput);
  }
});

passwordInput.addEventListener('blur', () => {
  if (passwordInput.value && !validatePassword(passwordInput.value)) {
    showError(passwordInput, I18N.passwordTooShort);
  } else {
    clearError(passwordInput);
  }
});

loginForm.addEventListener('submit', function (e) {
  e.preventDefault();

  clearError(emailInput);
  clearError(passwordInput);
  clearFormAlert();
  let isValid = true;

  if (!validateEmail(emailInput.value)) {
    showError(emailInput, I18N.invalidEmail);
    isValid = false;
  }
  if (!validatePassword(passwordInput.value)) {
    showError(passwordInput, I18N.passwordTooShort);
    isValid = false;
  }

  if (isValid) {
    submitButton.classList.add('loading');

    fetch("/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": CSRF_TOKEN
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
        window.location.href = data.redirect_url || "/dashboard";
      } else {
        showFormAlert(data.message || I18N.invalidCredentials, 'error');
      }
    })
    .catch(error => {
      submitButton.classList.remove('loading');
      showFormAlert(I18N.errorOccurred, 'error');
    });
  }
});

forgotPassword.addEventListener('click', e => {
  e.preventDefault();
  fpOpenModal();
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
