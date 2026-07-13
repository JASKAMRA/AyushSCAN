// Shared 3-step forgot-password flow, used by both login.html and dashboard.html.
// Each page defines window.FP_CONFIG before loading this script, since the two
// pages use different modal open/close mechanics and a different "reset succeeded" UI.
// Required shape:
//   window.FP_CONFIG = {
//     openModal: () => {...},
//     closeModal: () => {...},
//     onResetSuccess: (message) => {...},
//   };

const FP_CSRF_TOKEN = document.querySelector('meta[name="csrf-token"]').content;

function fpResetModalState() {
  ["fpStep1", "fpStep2", "fpStep3"].forEach((id, i) => {
    document.getElementById(id).style.display = i === 0 ? "block" : "none";
  });
  ["fpEmail", "fpOtp", "fpNewPass", "fpConfPass"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.value = "";
  });
  ["fpMsg1", "fpMsg2", "fpMsg3"].forEach((id) => {
    document.getElementById(id).textContent = "";
  });
}

function fpOpenModal() {
  fpResetModalState();
  window.FP_CONFIG.openModal();
}

function fpCloseModal() {
  window.FP_CONFIG.closeModal();
  fpResetModalState();
}

// login.html's #fpModal isn't part of dashboard.js's generic .modal Escape handler
// (dashboard.html's own forgot-password modal already has class="modal" and is covered there).
document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  const fpModal = document.getElementById("fpModal");
  if (fpModal && fpModal.style.display !== "none") fpCloseModal();
});

function _fpSetMsg(id, text, ok) {
  const el = document.getElementById(id);
  el.textContent = text;
  el.style.color = ok ? "#047857" : "#b91c1c";
}

async function fpSendOtp() {
  const email = document.getElementById("fpEmail").value.trim();
  if (!email) { _fpSetMsg("fpMsg1", I18N.enterEmail, false); return; }
  _fpSetMsg("fpMsg1", I18N.sendingOtp, true);
  try {
    const res = await fetch("/forgot_password", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": FP_CSRF_TOKEN },
      body: JSON.stringify({ email }),
    });
    const data = await res.json();
    _fpSetMsg("fpMsg1", data.message, data.success);
    if (data.success) {
      document.getElementById("fpStep1").style.display = "none";
      document.getElementById("fpStep2").style.display = "block";
    }
  } catch {
    _fpSetMsg("fpMsg1", I18N.networkError, false);
  }
}

async function fpVerifyOtp() {
  const email = document.getElementById("fpEmail").value.trim();
  const otp = document.getElementById("fpOtp").value.trim();
  if (!otp) { _fpSetMsg("fpMsg2", I18N.enterOtp, false); return; }
  _fpSetMsg("fpMsg2", I18N.verifying, true);
  try {
    const res = await fetch("/verify_otp", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": FP_CSRF_TOKEN },
      body: JSON.stringify({ email, otp }),
    });
    const data = await res.json();
    _fpSetMsg("fpMsg2", data.message, data.success);
    if (data.success) {
      document.getElementById("fpStep2").style.display = "none";
      document.getElementById("fpStep3").style.display = "block";
    }
  } catch {
    _fpSetMsg("fpMsg2", I18N.networkError, false);
  }
}

async function fpResetPassword() {
  const newPass = document.getElementById("fpNewPass").value;
  const confPass = document.getElementById("fpConfPass").value;
  if (newPass.length < 8) { _fpSetMsg("fpMsg3", I18N.passwordMin8, false); return; }
  if (newPass !== confPass) { _fpSetMsg("fpMsg3", I18N.passwordsDontMatch, false); return; }
  _fpSetMsg("fpMsg3", I18N.resetting, true);
  try {
    const res = await fetch("/reset_password", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": FP_CSRF_TOKEN },
      body: JSON.stringify({ new_password: newPass, confirm_password: confPass }),
    });
    const data = await res.json();
    if (data.success) {
      window.FP_CONFIG.closeModal();
      fpResetModalState();
      window.FP_CONFIG.onResetSuccess(data.message);
    } else {
      _fpSetMsg("fpMsg3", data.message, false);
    }
  } catch {
    _fpSetMsg("fpMsg3", I18N.networkError, false);
  }
}
