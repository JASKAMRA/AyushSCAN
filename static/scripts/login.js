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
        window.location.href = data.redirect_url || "/dashboard";
      } else {
        alert(data.message || "Invalid credentials!");
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
  fpClose();                                         // reset steps
  document.getElementById('fpModal').style.display = 'flex';
});

function fpClose() {
  document.getElementById('fpModal').style.display = 'none';
  ['fpStep1','fpStep2','fpStep3'].forEach((id, i) => {
    document.getElementById(id).style.display = i === 0 ? 'block' : 'none';
  });
  ['fpEmail','fpOtp','fpNewPass','fpConfPass'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  ['fpMsg1','fpMsg2','fpMsg3'].forEach(id => {
    document.getElementById(id).textContent = '';
  });
}

function _fpMsg(id, text, ok) {
  const el = document.getElementById(id);
  el.textContent = text;
  el.style.color = ok ? '#047857' : '#b91c1c';
}

async function fpSendOtp() {
  const email = document.getElementById('fpEmail').value.trim();
  if (!email) { _fpMsg('fpMsg1', 'Please enter your email.', false); return; }
  _fpMsg('fpMsg1', 'Sending OTP…', true);
  try {
    const res  = await fetch('/forgot_password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    const data = await res.json();
    _fpMsg('fpMsg1', data.message, data.success);
    if (data.success) {
      document.getElementById('fpStep1').style.display = 'none';
      document.getElementById('fpStep2').style.display = 'block';
    }
  } catch { _fpMsg('fpMsg1', 'Network error. Please try again.', false); }
}

async function fpVerifyOtp() {
  const email = document.getElementById('fpEmail').value.trim();
  const otp   = document.getElementById('fpOtp').value.trim();
  if (!otp) { _fpMsg('fpMsg2', 'Please enter the OTP.', false); return; }
  _fpMsg('fpMsg2', 'Verifying…', true);
  try {
    const res  = await fetch('/verify_otp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, otp }),
    });
    const data = await res.json();
    _fpMsg('fpMsg2', data.message, data.success);
    if (data.success) {
      document.getElementById('fpStep2').style.display = 'none';
      document.getElementById('fpStep3').style.display = 'block';
    }
  } catch { _fpMsg('fpMsg2', 'Network error. Please try again.', false); }
}

async function fpResetPassword() {
  const newPass  = document.getElementById('fpNewPass').value;
  const confPass = document.getElementById('fpConfPass').value;
  if (newPass.length < 8) { _fpMsg('fpMsg3', 'Password must be at least 8 characters.', false); return; }
  if (newPass !== confPass) { _fpMsg('fpMsg3', 'Passwords do not match.', false); return; }
  _fpMsg('fpMsg3', 'Resetting…', true);
  try {
    const res  = await fetch('/reset_password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ new_password: newPass, confirm_password: confPass }),
    });
    const data = await res.json();
    if (data.success) {
      fpClose();
      alert(data.message + ' You can now log in.');
    } else {
      _fpMsg('fpMsg3', data.message, false);
    }
  } catch { _fpMsg('fpMsg3', 'Network error. Please try again.', false); }
}

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
