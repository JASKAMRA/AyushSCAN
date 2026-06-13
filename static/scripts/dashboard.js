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
  form.querySelectorAll(".form-input").forEach((input) => {
    if (input.name !== "email") input.removeAttribute("readonly");
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
