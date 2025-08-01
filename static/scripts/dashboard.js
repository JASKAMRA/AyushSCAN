// ===== DOM ELEMENTS =====
const sidebar = document.getElementById("sidebar");
const sidebarOverlay = document.getElementById("sidebarOverlay");
const mainContent = document.getElementById("mainContent");
const menuToggle = document.getElementById("menuToggle");
const pageTitle = document.getElementById("pageTitle");
const navLinks = document.querySelectorAll(".nav-link");
const contentSections = document.querySelectorAll(".content-section");
const chatMessages = document.getElementById("chatMessages");
const chatInput = document.getElementById("chatInput");
function toggleDropdown() {
  const menu = document.getElementById("userDropdown");
  menu.style.display = menu.style.display === "block" ? "none" : "block";
}
document.addEventListener("click", function (e) {
  if (!e.target.closest(".user-profile") && !e.target.closest(".dropdown")) {
    document.getElementById("userDropdown").style.display = "none";
  }
});
function closeModal(id) {
  document.getElementById(id).style.display = "none";
}
window.onclick = function (event) {
  const modals = document.querySelectorAll(".modal");
  modals.forEach((modal) => {
    if (event.target === modal) {
      modal.style.display = "none";
    }
  });
};
function showFeedback(title, message) {
  document.getElementById("feedbackTitle").innerText = title;
  document.getElementById("feedbackMessage").innerText = message;
  openModal("feedbackModal");
}

// ===== NAVIGATION FUNCTIONS =====
function showSection(sectionId) {
  // Hide all sections
  contentSections.forEach((section) => {
    section.classList.remove("active");
  });

  // Show selected section
  const selectedSection = document.getElementById(sectionId);
  if (selectedSection) {
    selectedSection.classList.add("active");
  }

  // Update page title
  const sectionTitles = {
    dashboard: "Dashboard",
    scanner: "Scanner",
    profile: "Profile",
    chatbot: "AI Assistant",
    history: "Scan History",
    settings: "Settings",
  };
  pageTitle.textContent = sectionTitles[sectionId] || "Dashboard";

  // Update active nav link
  navLinks.forEach((link) => {
    link.classList.remove("active");
    if (link.getAttribute("data-section") === sectionId) {
      link.classList.add("active");
    }
  });

  // Close sidebar on mobile
  if (window.innerWidth <= 768) {
    toggleSidebar();
  }
}

function toggleSidebar() {
  sidebar.classList.toggle("mobile-visible");
  sidebarOverlay.classList.toggle("active");
}

// ===== EVENT LISTENERS =====
menuToggle.addEventListener("click", toggleSidebar);
sidebarOverlay.addEventListener("click", toggleSidebar);

navLinks.forEach((link) => {
  link.addEventListener("click", (e) => {
    e.preventDefault();
    const sectionId = link.getAttribute("data-section");
    showSection(sectionId);
  });
});

// ===== CHATBOT FUNCTIONALITY =====
function sendMessage() {
  const message = chatInput.value.trim();
  if (!message) return;

  // Add user message
  addMessage(message, "user");

  // Clear input
  chatInput.value = "";

  // Simulate bot response
  setTimeout(() => {
    const responses = [
      "I understand you're asking about your medical bill. Can you provide more specific details?",
      "Medical bills can be complex. Would you like me to explain any specific charges?",
      "I'm here to help you understand your healthcare costs. What specific information do you need?",
      "That's a great question about medical billing. Let me help you with that information.",
      "I can help clarify medical terms and procedures. What would you like to know more about?",
    ];
    const randomResponse =
      responses[Math.floor(Math.random() * responses.length)];
    addMessage(randomResponse, "bot");
  }, 1000);
}

function addMessage(text, sender) {
  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${sender}`;

  const avatarDiv = document.createElement("div");
  avatarDiv.className = "message-avatar";
  avatarDiv.textContent = sender === "user" ? "You" : "AI";

  const contentDiv = document.createElement("div");
  contentDiv.className = "message-content";
  contentDiv.textContent = text;

  messageDiv.appendChild(avatarDiv);
  messageDiv.appendChild(contentDiv);

  chatMessages.appendChild(messageDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}
// Scanner: Drag & Drop + Preview + Loading Spinner
const dropArea = document.getElementById("dropArea");
const fileInput = document.getElementById("fileInput");
const filePreview = document.getElementById("filePreview");
const fileName = document.getElementById("fileName");
const scanBtn = document.getElementById("scanBtn");
const loadingSpinner = document.getElementById("loadingSpinner");
const scannerForm = document.getElementById("scannerForm");

// Show file preview
fileInput.addEventListener("change", function () {
  if (this.files.length > 0) {
    filePreview.style.display = "block";
    fileName.textContent = this.files[0].name;
  } else {
    filePreview.style.display = "none";
  }
});

// Drag & drop support
dropArea.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropArea.style.borderColor = "var(--info)";
  dropArea.style.backgroundColor = "rgba(59,130,246,0.05)";
});

dropArea.addEventListener("dragleave", () => {
  dropArea.style.borderColor = "var(--border)";
  dropArea.style.backgroundColor = "var(--light-gray)";
});

dropArea.addEventListener("drop", (e) => {
  e.preventDefault();
  const files = e.dataTransfer.files;
  if (files.length > 0) {
    fileInput.files = files;
    fileInput.dispatchEvent(new Event("change"));
  }
});

// Show loading spinner on submit
scannerForm.addEventListener("submit", function (e) {
  e.preventDefault();

  if (!fileInput.files.length) {
    alert("Please select a file first.");
    return;
  }

  scanBtn.disabled = true;
  loadingSpinner.style.display = "block";

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  fetch("/scan", {
    method: "POST",
    body: formData,
  })
    .then((response) => response.json())
    .then((data) => {
      console.log("🟢 Received from backend:", data);

      scanBtn.disabled = false;
      loadingSpinner.style.display = "none";

      if (data.success && data.scan_id) {
        // Save scan result to localStorage
        localStorage.setItem("scanResults", JSON.stringify(data));

        // Redirect to result page
        window.location.href = `/result/${data.scan_id}`;
      } else {
        // ❌ Only show alert if scan truly failed
        alert("❌ Scan Failed: " + (data.message || "Unknown error"));
      }
    })
    .catch((error) => {
      scanBtn.disabled = false;
      loadingSpinner.style.display = "none";
      alert("Something went wrong: " + error.message);
    });
});

const params = new URLSearchParams(window.location.search);
const msg = params.get("message");
if (msg) {
  showFeedback("Success", msg);
  history.replaceState({}, document.title, window.location.pathname);
}
function openModal(id) {
  document.getElementById(id).style.display = "block";
}

function closeModal(id) {
  document.getElementById(id).style.display = "none";
}

// Close modal on outside click
window.onclick = function (event) {
  const modals = document.querySelectorAll(".modal");
  modals.forEach((modal) => {
    if (event.target === modal) modal.style.display = "none";
  });
};

function enableEditing() {
  const form = document.getElementById("updateProfileForm");
  const inputs = form.querySelectorAll(".form-input");
  inputs.forEach((input) => {
    if (input.name !== "email") {
      input.removeAttribute("readonly");
    }
  });

  // Show Save, Hide Edit
  document.querySelector(".btn-profile-update").classList.add("hidden");
  document.querySelector(".btn-profile-save").classList.remove("hidden");

  // Scroll to top of form
  form.scrollIntoView({ behavior: "smooth" });
}

// ===== HOSPITALS NEARBY: OpenStreetMap Overpass Integration =====
document.addEventListener("DOMContentLoaded", () => {
  const hospitalSection = document.getElementById("Hospitals Nearby");
  if (hospitalSection) {
    const locationStatus = document.getElementById("locationStatus");
    const hospitalList = document.getElementById("hospitalList");

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;
        locationStatus.textContent = `📍 Location: ${latitude.toFixed(
          3
        )}, ${longitude.toFixed(3)}`;

        const query = `
          [out:json];
          (
            node["amenity"="hospital"](around:5000,${latitude},${longitude});
          );
          out body;
        `;

        try {
          const res = await fetch("https://overpass-api.de/api/interpreter", {
            method: "POST",
            body: query,
          });
          const data = await res.json();
          const hospitals = data.elements;

          if (hospitals.length === 0) {
            hospitalList.innerHTML = `<li>No hospitals found nearby.</li>`;
          } else {
            hospitalList.innerHTML = hospitals
              .map((h) => `<li>🏥 ${h.tags.name || "Unnamed Hospital"}</li>`)
              .join("");
          }
        } catch (err) {
          hospitalList.innerHTML = `<li>Error fetching hospital data.</li>`;
          console.error("Overpass fetch error:", err);
        }
      },
      (err) => {
        locationStatus.textContent =
          "⚠️ Location access denied. Cannot fetch nearby hospitals.";
        console.warn("Geolocation error:", err);
      }
    );
  }
});
