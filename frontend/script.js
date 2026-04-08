// ═══════════════════════════════════════════
// CLIP CURATOR — script.js
// Connects frontend to Flask backend
// ═══════════════════════════════════════════

const API = "http://localhost:5000";

// Stores current logged-in username
let currentUser = "";

// Stores current analysis results
let currentResult = null;

// ── PAGE & SECTION SWITCHING ─────────────────

function showPage(pageId) {
  document.querySelectorAll('.page').forEach(p => {
    p.classList.remove('active');
    p.classList.add('hidden');
  });
  const page = document.getElementById(pageId);
  if (page) {
    page.classList.remove('hidden');
    page.classList.add('active');
  }
}

function showAppSection(section) {
  // Hide all sections
  document.getElementById('section-home').classList.add('hidden');
  document.getElementById('section-library').classList.add('hidden');

  // Update nav buttons
  document.getElementById('nav-home').classList.remove('active');
  document.getElementById('nav-library').classList.remove('active');

  if (section === 'home') {
    document.getElementById('section-home').classList.remove('hidden');
    document.getElementById('nav-home').classList.add('active');
  } else {
    document.getElementById('section-library').classList.remove('hidden');
    document.getElementById('nav-library').classList.add('active');
    loadLibrary();
  }
}

// ── AUTH TAB SWITCHING ───────────────────────

function switchTab(tab) {
  document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));

  if (tab === 'login') {
    document.getElementById('form-login').classList.remove('hidden');
    document.getElementById('form-signup').classList.add('hidden');
    document.querySelectorAll('.auth-tab')[0].classList.add('active');
  } else {
    document.getElementById('form-login').classList.add('hidden');
    document.getElementById('form-signup').classList.remove('hidden');
    document.querySelectorAll('.auth-tab')[1].classList.add('active');
  }
}

// ── LOGIN ────────────────────────────────────

async function handleLogin() {
  const username = document.getElementById('login-user').value.trim();
  const password = document.getElementById('login-pass').value.trim();
  const errEl = document.getElementById('login-error');

  if (!username || !password) {
    errEl.textContent = "Please enter username and password.";
    errEl.classList.remove('hidden');
    return;
  }

  try {
    const res = await fetch(`${API}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    const data = await res.json();

    if (data.success) {
      errEl.classList.add('hidden');
      currentUser = data.username;
      localStorage.setItem('cc_user', currentUser);
      document.getElementById('nav-username').textContent = currentUser;
      showPage('page-app');
      showAppSection('home');
    } else {
      errEl.textContent = data.error || "Incorrect credentials.";
      errEl.classList.remove('hidden');
    }
  } catch (e) {
    errEl.textContent = "Cannot connect to server. Is Flask running?";
    errEl.classList.remove('hidden');
  }
}

// ── SIGNUP ───────────────────────────────────

async function handleSignup() {
  const username = document.getElementById('signup-user').value.trim();
  const password = document.getElementById('signup-pass').value.trim();
  const errEl = document.getElementById('signup-error');
  const succEl = document.getElementById('signup-success');

  errEl.classList.add('hidden');
  succEl.classList.add('hidden');

  if (!username || !password) {
    errEl.textContent = "Please fill in all fields.";
    errEl.classList.remove('hidden');
    return;
  }

  try {
    const res = await fetch(`${API}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    const data = await res.json();

    if (data.success) {
      succEl.textContent = "Account created! You can now sign in.";
      succEl.classList.remove('hidden');
      document.getElementById('signup-user').value = '';
      document.getElementById('signup-pass').value = '';
      // Switch to login tab after 1.5 seconds
      setTimeout(() => switchTab('login'), 1500);
    } else {
      errEl.textContent = data.error || "Signup failed.";
      errEl.classList.remove('hidden');
    }
  } catch (e) {
    errEl.textContent = "Cannot connect to server. Is Flask running?";
    errEl.classList.remove('hidden');
  }
}

// ── LOGOUT ───────────────────────────────────

function handleLogout() {
  localStorage.removeItem('cc_user');
  currentUser = "";
  currentResult = null;
  document.getElementById('results-area').classList.add('hidden');
  document.getElementById('url-input').value = '';
  showPage('page-login');
}

// ── CHECK AUTO LOGIN ─────────────────────────

function checkAutoLogin() {
  const saved = localStorage.getItem('cc_user');
  if (saved) {
    currentUser = saved;
    document.getElementById('nav-username').textContent = currentUser;
    showPage('page-app');
    showAppSection('home');
  } else {
    showPage('page-login');
  }
}

// ── ANALYZE VIDEO ────────────────────────────

async function analyzeVideo() {
  const url = document.getElementById('url-input').value.trim();
  const errEl = document.getElementById('analyze-error');
  const loadingEl = document.getElementById('loading-area');
  const loaderText = document.getElementById('loader-text');
  const analyzeBtn = document.getElementById('analyze-btn');

  if (!url) {
    errEl.textContent = "Please paste a YouTube URL first!";
    errEl.classList.remove('hidden');
    return;
  }

  // Hide old results and errors
  errEl.classList.add('hidden');
  document.getElementById('results-area').classList.add('hidden');

  // Show loading
  loadingEl.classList.remove('hidden');
  analyzeBtn.disabled = true;
  analyzeBtn.textContent = "Analyzing...";

  // Animate loading text
  const steps = [
    "Fetching video info...",
    "Getting transcript...",
    "AI is reading the content...",
    "Generating topic summaries...",
    "Almost done..."
  ];
  let stepIndex = 0;
  const stepInterval = setInterval(() => {
    if (stepIndex < steps.length) {
      loaderText.textContent = steps[stepIndex];
      stepIndex++;
    }
  }, 4000);

  try {
    const res = await fetch(`${API}/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });

    const data = await res.json();
    clearInterval(stepInterval);

    if (data.success) {
      currentResult = data;
      displayResults(data);
    } else {
      errEl.textContent = data.error || "Something went wrong. Please try again.";
      errEl.classList.remove('hidden');
    }

  } catch (e) {
    clearInterval(stepInterval);
    errEl.textContent = "Cannot connect to Flask server. Make sure it's running on port 5000.";
    errEl.classList.remove('hidden');
  } finally {
    loadingEl.classList.add('hidden');
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = "Analyze →";
  }
}

// ── DISPLAY RESULTS ──────────────────────────

function displayResults(data) {
  // Video info
  document.getElementById('result-thumbnail').src = data.thumbnail;
  document.getElementById('result-title').textContent = data.title;
  document.getElementById('result-channel').textContent = "📺 " + (data.channel || 'Unknown Channel');
  document.getElementById('result-duration').textContent = "⏱ Duration: " + data.duration_formatted;
  document.getElementById('result-method').textContent =
    data.transcript_method === 'captions' ? '✅ YouTube Captions' : '🎙 Whisper Transcription';

  // Overall summary bullets
  const summaryList = document.getElementById('overall-summary-list');
  summaryList.innerHTML = '';
  (data.overall_summary || []).forEach(point => {
    const li = document.createElement('li');
    li.textContent = point;
    summaryList.appendChild(li);
  });

  // Topics
  const topicsList = document.getElementById('topics-list');
  topicsList.innerHTML = '';
  document.getElementById('topics-count').textContent =
    `${data.topics.length} topics found`;

  data.topics.forEach((topic, index) => {
    const card = document.createElement('div');
    card.className = 'topic-card';
    card.innerHTML = `
      <div class="topic-top">
        <span class="topic-num">${topic.topic_number || index + 1}</span>
        <span class="topic-title-text">${topic.title}</span>
        <span class="time-badge">🕐 ${topic.start_formatted} – ${topic.end_formatted}</span>
      </div>
      <p class="topic-summary">${topic.summary}</p>
      <div class="topic-actions">
        <a class="btn-jump"
           href="${topic.youtube_link}"
           target="_blank"
           rel="noopener noreferrer">
          ▶ Jump on YouTube
        </a>
        <button class="btn-save" id="save-btn-${index}"
                onclick="saveTopic(${index})">
          🔖 Save
        </button>
      </div>
    `;
    topicsList.appendChild(card);
  });

  // Clip section — show or hide based on duration
  const clipForm = document.getElementById('clip-form');
  const clipNotice = document.getElementById('clip-unavailable');

  if (data.duration > 600) {
    // Video is over 10 minutes — disable clip
    clipForm.classList.add('hidden');
    clipNotice.classList.remove('hidden');
  } else {
    clipForm.classList.remove('hidden');
    clipNotice.classList.add('hidden');
    document.getElementById('clip-status').classList.add('hidden');
  }

  // Show results area
  document.getElementById('results-area').classList.remove('hidden');

  // Scroll down smoothly to results
  document.getElementById('results-area').scrollIntoView({ behavior: 'smooth' });
}

// ── SAVE TOPIC ───────────────────────────────

async function saveTopic(index) {
  if (!currentResult) return;

  const topic = currentResult.topics[index];
  const btn = document.getElementById(`save-btn-${index}`);

  btn.textContent = "Saving...";
  btn.disabled = true;

  try {
    const res = await fetch(`${API}/bookmarks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username:        currentUser,
        video_id:        currentResult.video_id,
        video_title:     currentResult.title,
        topic_title:     topic.title,
        start_time:      topic.start_time,
        end_time:        topic.end_time,
        start_formatted: topic.start_formatted,
        end_formatted:   topic.end_formatted,
        summary:         topic.summary,
        youtube_link:    topic.youtube_link
      })
    });

    const data = await res.json();

    if (data.success) {
      btn.textContent = "✓ Saved";
      btn.classList.add('saved');
    } else {
      btn.textContent = "🔖 Save";
      btn.disabled = false;
      alert("Save failed: " + (data.error || "Unknown error"));
    }

  } catch (e) {
    btn.textContent = "🔖 Save";
    btn.disabled = false;
    alert("Error connecting to backend.");
  }
}

// ── DOWNLOAD CLIP ────────────────────────────

async function downloadClip() {
  if (!currentResult) return;

  const startInput = document.getElementById('clip-start').value.trim();
  const endInput = document.getElementById('clip-end').value.trim();
  const statusEl = document.getElementById('clip-status');

  // Convert MM:SS to seconds
  function timeToSeconds(timeStr) {
    if (!timeStr) return NaN;
    const parts = timeStr.split(':').map(Number);
    if (parts.some(isNaN)) return NaN;
    if (parts.length === 1) return parts[0];
    if (parts.length === 2) return parts[0] * 60 + parts[1];
    if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
    return NaN;
  }

  const start = timeToSeconds(startInput);
  const end = timeToSeconds(endInput);

  if (isNaN(start) || isNaN(end)) {
    statusEl.textContent = "⚠️ Please enter valid times like 0:30 or 1:05";
    statusEl.style.color = "#ff6b6b";
    statusEl.classList.remove('hidden');
    return;
  }

  if (end <= start) {
    statusEl.textContent = "⚠️ End time must be greater than start time.";
    statusEl.style.color = "#ff6b6b";
    statusEl.classList.remove('hidden');
    return;
  }

  if (end - start > 300) {
    statusEl.textContent = "⚠️ Maximum clip length is 5 minutes (5:00).";
    statusEl.style.color = "#ff6b6b";
    statusEl.classList.remove('hidden');
    return;
  }

  statusEl.textContent = "⏳ Downloading and cutting clip... Please wait.";
  statusEl.style.color = "#888";
  statusEl.classList.remove('hidden');

  try {
    const res = await fetch(`${API}/clip`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        video_id:   currentResult.video_id,
        start_time: start,
        end_time:   end,
        duration:   currentResult.duration
      })
    });

    if (res.ok) {
      const blob = await res.blob();
      const downloadUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `clip_${currentResult.video_id}_${startInput.replace(':','-')}.mp4`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(downloadUrl);
      statusEl.textContent = "✅ Clip downloaded successfully!";
      statusEl.style.color = "#4ade80";
    } else {
      const err = await res.json();
      statusEl.textContent = "❌ " + (err.error || "Clip failed.");
      statusEl.style.color = "#ff6b6b";
    }
  } catch (e) {
    statusEl.textContent = "❌ Error connecting to backend.";
    statusEl.style.color = "#ff6b6b";
  }
}

// ── LIBRARY ──────────────────────────────────

async function loadLibrary() {
  const container = document.getElementById('library-list');
  container.innerHTML = '<p class="empty-msg">Loading your saved clips...</p>';

  try {
    const res = await fetch(`${API}/bookmarks?username=${encodeURIComponent(currentUser)}`);
    const data = await res.json();
    renderLibrary(data.bookmarks || []);
  } catch (e) {
    container.innerHTML = '<p class="empty-msg">Could not load library. Is Flask running?</p>';
  }
}

async function searchLibrary() {
  const query = document.getElementById('search-input').value.trim();

  if (!query) {
    loadLibrary();
    return;
  }

  try {
    const res = await fetch(
      `${API}/bookmarks/search?username=${encodeURIComponent(currentUser)}&q=${encodeURIComponent(query)}`
    );
    const data = await res.json();
    renderLibrary(data.results || []);
  } catch (e) {
    console.error("Search error:", e);
  }
}

function renderLibrary(bookmarks) {
  const container = document.getElementById('library-list');
  container.innerHTML = '';

  if (bookmarks.length === 0) {
    container.innerHTML = '<p class="empty-msg">No saved clips found. Analyze a video and save topics you like!</p>';
    return;
  }

  bookmarks.forEach(bm => {
    const card = document.createElement('div');
    card.className = 'bookmark-card';
    card.innerHTML = `
      <div class="bookmark-info">
        <div class="bookmark-top">
          <span class="time-badge">🕐 ${bm.start_formatted} – ${bm.end_formatted}</span>
        </div>
        <p class="bookmark-topic">${bm.topic_title || 'Saved Topic'}</p>
        <p class="bookmark-video">📺 ${bm.video_title || 'Unknown Video'}</p>
        <p class="bookmark-summary">${bm.summary || ''}</p>
        <div class="bookmark-actions">
          <a class="btn-open"
             href="${bm.youtube_link}"
             target="_blank"
             rel="noopener noreferrer">
            ▶ Open in YouTube
          </a>
        </div>
      </div>
      <button class="btn-delete" onclick="deleteBookmark(${bm.id})" title="Delete">🗑</button>
    `;
    container.appendChild(card);
  });
}

async function deleteBookmark(id) {
  if (!confirm("Delete this saved clip?")) return;

  try {
    await fetch(`${API}/bookmarks/${id}`, { method: 'DELETE' });
    loadLibrary();
  } catch (e) {
    alert("Could not delete. Is Flask running?");
  }
}

// ── KEYBOARD SHORTCUTS ───────────────────────

document.addEventListener('DOMContentLoaded', () => {
  // Press Enter in URL bar to analyze
  const urlInput = document.getElementById('url-input');
  if (urlInput) {
    urlInput.addEventListener('keydown', e => {
      if (e.key === 'Enter') analyzeVideo();
    });
  }

  // Press Enter in login fields
  document.getElementById('login-pass')?.addEventListener('keydown', e => {
    if (e.key === 'Enter') handleLogin();
  });

  // Auto login check
  checkAutoLogin();
});