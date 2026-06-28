const sidebar = document.getElementById("sidebar");
const sidebarOverlay = document.getElementById("sidebarOverlay");
const menuToggle = document.getElementById("menuToggle");
const pageTitle = document.getElementById("pageTitle");
const navLinks = document.querySelectorAll(".nav-link");
const contentSections = document.querySelectorAll(".content-section");

function showSection(sectionId) {
  contentSections.forEach((section) => section.classList.remove("active"));
  const selectedSection = document.getElementById(sectionId);
  if (selectedSection) selectedSection.classList.add("active");

  const activeLink = Array.from(navLinks).find((link) => link.dataset.section === sectionId);
  navLinks.forEach((link) => link.classList.remove("active"));
  if (activeLink) {
    activeLink.classList.add("active");
    pageTitle.textContent = activeLink.querySelector(".nav-text").textContent;
  }

  if (window.innerWidth <= 768 && sidebar.classList.contains("mobile-visible")) {
    toggleSidebar();
  }
}

function toggleSidebar() {
  sidebar.classList.toggle("mobile-visible");
  sidebarOverlay.classList.toggle("active");
}

function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.style.display = "block";
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.style.display = "none";
}

function showFeedback(title, message) {
  document.getElementById("feedbackTitle").innerText = title;
  document.getElementById("feedbackMessage").innerText = message;
  openModal("feedbackModal");
}

function enableEditing() {
  const form = document.getElementById("updateProfileForm");
  form.querySelectorAll(".form-input").forEach((el) => {
    if (el.name !== "email") {
      el.removeAttribute("readonly");
      el.removeAttribute("disabled");
    }
  });
  document.querySelector(".btn-profile-update").classList.add("hidden");
  document.querySelector(".btn-profile-save").classList.remove("hidden");
  form.scrollIntoView({ behavior: "smooth" });
}

menuToggle.addEventListener("click", toggleSidebar);
sidebarOverlay.addEventListener("click", toggleSidebar);
navLinks.forEach((link) => {
  link.addEventListener("click", (event) => {
    event.preventDefault();
    showSection(link.dataset.section);
  });
});

window.addEventListener("click", (event) => {
  document.querySelectorAll(".modal").forEach((modal) => {
    if (event.target === modal) modal.style.display = "none";
  });
});

const dropArea = document.getElementById("dropArea");
const fileInput = document.getElementById("fileInput");
const filePreview = document.getElementById("filePreview");
const fileName = document.getElementById("fileName");
const scanBtn = document.getElementById("scanBtn");
const loadingSpinner = document.getElementById("loadingSpinner");
const scannerForm = document.getElementById("scannerForm");

fileInput.addEventListener("change", function () {
  if (this.files.length > 0) {
    filePreview.style.display = "block";
    fileName.textContent = this.files[0].name;
  } else {
    filePreview.style.display = "none";
  }
});

dropArea.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropArea.style.borderColor = "var(--info)";
  dropArea.style.backgroundColor = "rgba(45,182,70,0.05)";
});

dropArea.addEventListener("dragleave", () => {
  dropArea.style.borderColor = "var(--border)";
  dropArea.style.backgroundColor = "var(--light-gray)";
});

dropArea.addEventListener("drop", (event) => {
  event.preventDefault();
  if (event.dataTransfer.files.length > 0) {
    fileInput.files = event.dataTransfer.files;
    fileInput.dispatchEvent(new Event("change"));
  }
});

scannerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!fileInput.files.length) {
    showFeedback("Scan", "Please select a file first.");
    return;
  }

  scanBtn.disabled = true;
  loadingSpinner.style.display = "block";

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  try {
    const response = await fetch("/scan", { method: "POST", body: formData });
    const data = await response.json();
    if (data.success && data.scan_id) {
      window.location.href = `/result/${data.scan_id}`;
      return;
    }
    showFeedback("Scan failed", data.message || "Unknown error");
  } catch (error) {
    showFeedback("Scan failed", error.message);
  } finally {
    scanBtn.disabled = false;
    loadingSpinner.style.display = "none";
  }
});

function renderHospitals(hospitals) {
  const hospitalList = document.getElementById("hospitalList");
  if (!hospitals.length) {
    hospitalList.innerHTML = "<p>No hospitals found for the selected filter.</p>";
    return;
  }
  hospitalList.innerHTML = hospitals
    .map((hospital) => `
      <article style="border:1px solid #e5e7eb;border-radius:8px;padding:1rem;background:${hospital.ayushman ? "#ecfdf5" : "#fff"};">
        <h3 style="margin-bottom:.5rem;">${hospital.name}</h3>
        <p>${hospital.address}</p>
        <p>Distance: ${hospital.distance} km</p>
        <p>Contact: ${hospital.contact}</p>
        <p>${hospital.ayushman ? "Marked as possible Ayushman Bharat/PM-JAY hospital" : "Ayushman Bharat status not confirmed"}</p>
        <a href="${hospital.map_url}" target="_blank" rel="noopener">Open map</a>
      </article>
    `)
    .join("");
}

document.getElementById("findHospitalsBtn").addEventListener("click", () => {
  const status = document.getElementById("locationStatus");
  const ayushmanOnly = document.getElementById("ayushmanOnly").checked ? "1" : "0";

  if (!navigator.geolocation) {
    status.textContent = "Browser geolocation is not supported.";
    return;
  }

  status.textContent = "Getting location...";
  navigator.geolocation.getCurrentPosition(
    async ({ coords }) => {
      status.textContent = `Location: ${coords.latitude.toFixed(3)}, ${coords.longitude.toFixed(3)}`;
      try {
        const response = await fetch(`/hospitals/nearby?lat=${coords.latitude}&lon=${coords.longitude}&ayushman=${ayushmanOnly}`);
        const data = await response.json();
        if (!data.success) {
          status.textContent = data.message || "Hospital search failed.";
        }
        renderHospitals(data.hospitals || []);
      } catch (error) {
        status.textContent = "Hospital search is temporarily unavailable.";
      }
    },
    () => {
      status.textContent = "Location access denied. Enable location permission to search nearby hospitals.";
    }
  );
});

const params = new URLSearchParams(window.location.search);
const msg = params.get("message");
if (msg) {
  showFeedback("AyushScan", msg);
  history.replaceState({}, document.title, window.location.pathname);
}

// ── Forgot-password 3-step flow ───────────────────────────────────────────
function closeFpModal() {
  closeModal("forgotPasswordModal");
  ["fpStep1","fpStep2","fpStep3"].forEach((id, i) => {
    document.getElementById(id).style.display = i === 0 ? "block" : "none";
  });
  ["fpEmail","fpOtp","fpNewPass","fpConfPass"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = "";
  });
  ["fpMsg1","fpMsg2","fpMsg3"].forEach(id => {
    document.getElementById(id).textContent = "";
  });
}

function _fpSetMsg(id, text, ok) {
  const el = document.getElementById(id);
  el.textContent = text;
  el.style.color = ok ? "#047857" : "#b91c1c";
}

async function fpSendOtp() {
  const email = document.getElementById("fpEmail").value.trim();
  if (!email) { _fpSetMsg("fpMsg1", "Please enter your email.", false); return; }
  _fpSetMsg("fpMsg1", "Sending OTP…", true);
  try {
    const res = await fetch("/forgot_password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    const data = await res.json();
    _fpSetMsg("fpMsg1", data.message, data.success);
    if (data.success) {
      document.getElementById("fpStep1").style.display = "none";
      document.getElementById("fpStep2").style.display = "block";
    }
  } catch {
    _fpSetMsg("fpMsg1", "Network error. Please try again.", false);
  }
}

async function fpVerifyOtp() {
  const email = document.getElementById("fpEmail").value.trim();
  const otp   = document.getElementById("fpOtp").value.trim();
  if (!otp) { _fpSetMsg("fpMsg2", "Please enter the OTP.", false); return; }
  _fpSetMsg("fpMsg2", "Verifying…", true);
  try {
    const res = await fetch("/verify_otp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, otp }),
    });
    const data = await res.json();
    _fpSetMsg("fpMsg2", data.message, data.success);
    if (data.success) {
      document.getElementById("fpStep2").style.display = "none";
      document.getElementById("fpStep3").style.display = "block";
    }
  } catch {
    _fpSetMsg("fpMsg2", "Network error. Please try again.", false);
  }
}

async function fpResetPassword() {
  const newPass  = document.getElementById("fpNewPass").value;
  const confPass = document.getElementById("fpConfPass").value;
  if (newPass.length < 8) { _fpSetMsg("fpMsg3", "Password must be at least 8 characters.", false); return; }
  if (newPass !== confPass) { _fpSetMsg("fpMsg3", "Passwords do not match.", false); return; }
  _fpSetMsg("fpMsg3", "Resetting…", true);
  try {
    const res = await fetch("/reset_password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ new_password: newPass, confirm_password: confPass }),
    });
    const data = await res.json();
    if (data.success) {
      closeFpModal();
      showFeedback("Password Reset", data.message);
    } else {
      _fpSetMsg("fpMsg3", data.message, false);
    }
  } catch {
    _fpSetMsg("fpMsg3", "Network error. Please try again.", false);
  }
}
