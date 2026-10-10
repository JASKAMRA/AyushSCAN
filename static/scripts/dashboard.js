const sidebar = document.getElementById("sidebar");
const sidebarOverlay = document.getElementById("sidebarOverlay");
const menuToggle = document.getElementById("menuToggle");
const pageTitle = document.getElementById("pageTitle");
const navLinks = document.querySelectorAll(".nav-link");
const contentSections = document.querySelectorAll(".content-section");
const feedbackTitleEl = document.getElementById("feedbackTitle");
const feedbackMessageEl = document.getElementById("feedbackMessage");
const CSRF_TOKEN = document.querySelector('meta[name="csrf-token"]').content;

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
  feedbackTitleEl.innerText = title;
  feedbackMessageEl.innerText = message;
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

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  document.querySelectorAll(".modal").forEach((modal) => {
    if (modal.style.display === "block") modal.style.display = "none";
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
    showFeedback(I18N.scanTitle, I18N.pleaseSelectFile);
    return;
  }

  scanBtn.disabled = true;
  loadingSpinner.style.display = "block";

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  try {
    const response = await fetch("/scan", {
      method: "POST",
      headers: { "X-CSRFToken": CSRF_TOKEN },
      body: formData,
    });
    const data = await response.json();
    if (data.success && data.review_url) {
      window.location.href = data.review_url;
      return;
    }
    if (data.success && data.scan_id) {
      window.location.href = `/result/${data.scan_id}`;
      return;
    }
    showFeedback(I18N.scanFailedTitle, data.message || I18N.unknownError);
  } catch (error) {
    showFeedback(I18N.scanFailedTitle, error.message);
  } finally {
    scanBtn.disabled = false;
    loadingSpinner.style.display = "none";
  }
});

function renderHospitalSkeleton() {
  const hospitalList = document.getElementById("hospitalList");
  hospitalList.innerHTML = Array(3)
    .fill('<article class="hospital-skeleton" aria-hidden="true"><div class="skel-line skel-line-title"></div><div class="skel-line"></div><div class="skel-line skel-line-short"></div></article>')
    .join("");
}

function renderHospitals(hospitals) {
  const hospitalList = document.getElementById("hospitalList");
  const escapeHtml = (value) =>
    String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");

  if (!hospitals.length) {
    hospitalList.innerHTML = `<p class="empty-state">${I18N.noHospitalsFound}</p>`;
    return;
  }
  hospitalList.innerHTML = hospitals
    .map((hospital) => {
      const distance = Number(hospital.distance || 0).toFixed(2);
      return `
      <article style="border:1px solid #e5e7eb;border-radius:8px;padding:1rem;background:${hospital.ayushman ? "#ecfdf5" : "#fff"};">
        <h3 style="margin-bottom:.5rem;">${escapeHtml(hospital.name)}</h3>
        <p>${escapeHtml(hospital.type || "Healthcare")}</p>
        <p>${escapeHtml(hospital.address)}</p>
        <p>${I18N.distanceLabel.replace("%(km)s", distance)}</p>
        <p>${I18N.contactLabel.replace("%(contact)s", escapeHtml(hospital.contact))}</p>
        <p>${hospital.ayushman ? I18N.ayushmanPossible : I18N.ayushmanUnknown}</p>
        <a href="${escapeHtml(hospital.map_url)}" target="_blank" rel="noopener">${I18N.openMap}</a>
      </article>
    `;
    })
    .join("");
}

document.getElementById("findHospitalsBtn").addEventListener("click", () => {
  const status = document.getElementById("locationStatus");
  const ayushmanOnly = document.getElementById("ayushmanOnly").checked ? "1" : "0";

  if (!navigator.geolocation) {
    status.textContent = I18N.geolocationUnsupported;
    return;
  }

  status.textContent = I18N.gettingLocation;
  navigator.geolocation.getCurrentPosition(
    async ({ coords }) => {
      status.textContent = I18N.locationLabel.replace("%(lat)s", coords.latitude.toFixed(3)).replace("%(lon)s", coords.longitude.toFixed(3));
      renderHospitalSkeleton();
      try {
        const response = await fetch(`/hospitals/nearby?lat=${coords.latitude}&lon=${coords.longitude}&ayushman=${ayushmanOnly}`);
        const data = await response.json();
        if (!data.success) {
          status.textContent = data.message || I18N.hospitalSearchFailed;
        }
        renderHospitals(data.hospitals || []);
      } catch (error) {
        status.textContent = I18N.hospitalSearchUnavailable;
      }
    },
    () => {
      status.textContent = I18N.locationDenied;
    }
  );
});

const params = new URLSearchParams(window.location.search);
const msg = params.get("message");
if (msg) {
  showFeedback(I18N.appName, msg);
  history.replaceState({}, document.title, window.location.pathname);
}
