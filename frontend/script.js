// API base URL - use relative path to work from any host
const API_URL = '/api';

// Global state
let currentSessionId = null;

// DOM elements
let chatMessages, chatInput, sendButton, totalCourses, courseTitles, themeToggle;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements after page loads
    chatMessages = document.getElementById('chatMessages');
    chatInput = document.getElementById('chatInput');
    sendButton = document.getElementById('sendButton');
    totalCourses = document.getElementById('totalCourses');
    courseTitles = document.getElementById('courseTitles');
    themeToggle = document.getElementById('themeToggle');

    initTheme();
    setupEventListeners();
    createNewSession();
    loadCourseStats();
});

// Event Listeners
function setupEventListeners() {
    // Theme toggle
    themeToggle.addEventListener('click', toggleTheme);

    // Chat functionality
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    // Suggested questions
    document.querySelectorAll('.suggested-item').forEach(button => {
        button.addEventListener('click', (e) => {
            const question = e.currentTarget.getAttribute('data-question');
            chatInput.value = question;
            sendMessage();
        });
    });
}


// Chat Functions
async function sendMessage() {
    const query = chatInput.value.trim();
    if (!query) return;

    chatInput.value = '';
    chatInput.disabled = true;
    sendButton.disabled = true;

    addMessage(query, 'user');

    // Create assistant message div with loading dots
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = `<div class="loading"><span></span><span></span><span></span></div>`;
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    let fullText = '';
    let firstChunk = true;

    try {
        const response = await fetch(`${API_URL}/query/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, session_id: currentSessionId })
        });

        if (!response.ok) throw new Error('Query failed');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                let data;
                try { data = JSON.parse(line.slice(6)); } catch { continue; }

                if (data.error) {
                    contentDiv.textContent = `Erreur : ${data.error}`;
                }

                if (data.text) {
                    if (firstChunk) {
                        contentDiv.innerHTML = '';
                        firstChunk = false;
                    }
                    fullText += data.text;
                    contentDiv.textContent = fullText;
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                    await new Promise(r => setTimeout(r, 0));
                }

                if (data.done) {
                    if (!currentSessionId) currentSessionId = data.session_id;
                    contentDiv.innerHTML = marked.parse(fullText);
                    if (data.sources && data.sources.length > 0) {
                        const sourcesEl = document.createElement('details');
                        sourcesEl.className = 'sources-collapsible';
                        sourcesEl.innerHTML = `
                            <summary class="sources-header">Sources</summary>
                            <div class="sources-content">${data.sources.join(', ')}</div>
                        `;
                        messageDiv.appendChild(sourcesEl);
                    }
                    const badge = document.createElement('span');
                    badge.className = 'ragas-badge pending';
                    badge.textContent = '⏳ évaluation…';
                    messageDiv.appendChild(badge);

                    const thumbs = document.createElement('span');
                    thumbs.className = 'thumbs-container';
                    const upBtn = document.createElement('button');
                    upBtn.className = 'thumb-btn';
                    upBtn.textContent = '👍';
                    upBtn.title = 'Bonne réponse';
                    const downBtn = document.createElement('button');
                    downBtn.className = 'thumb-btn';
                    downBtn.textContent = '👎';
                    downBtn.title = 'Réponse insuffisante';
                    thumbs.appendChild(upBtn);
                    thumbs.appendChild(downBtn);
                    messageDiv.appendChild(thumbs);

                    const capturedQuery = query;
                    upBtn.addEventListener('click', () => sendFeedback(1, capturedQuery, upBtn, downBtn));
                    downBtn.addEventListener('click', () => sendFeedback(-1, capturedQuery, upBtn, downBtn));

                    chatMessages.scrollTop = chatMessages.scrollHeight;
                    pollRagasScore(badge);
                }
            }
        }
    } catch (error) {
        contentDiv.textContent = `Error: ${error.message}`;
    } finally {
        chatInput.disabled = false;
        sendButton.disabled = false;
        chatInput.focus();
    }
}

function createLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="loading">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    return messageDiv;
}

function addMessage(content, type, sources = null, isWelcome = false) {
    const messageId = Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}${isWelcome ? ' welcome-message' : ''}`;
    messageDiv.id = `message-${messageId}`;
    
    // Convert markdown to HTML for assistant messages
    const displayContent = type === 'assistant' ? marked.parse(content) : escapeHtml(content);
    
    let html = `<div class="message-content">${displayContent}</div>`;
    
    if (sources && sources.length > 0) {
        html += `
            <details class="sources-collapsible">
                <summary class="sources-header">Sources</summary>
                <div class="sources-content">${sources.join(', ')}</div>
            </details>
        `;
    }
    
    messageDiv.innerHTML = html;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return messageId;
}

// Helper function to escape HTML for user messages
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Removed removeMessage function - no longer needed since we handle loading differently

async function createNewSession() {
    currentSessionId = null;
    chatMessages.innerHTML = '';
    addMessage('Welcome to the Course Materials Assistant! I can help you with questions about courses, lessons and specific content. What would you like to know?', 'assistant', null, true);
}

// Theme Functions
function initTheme() {
    const saved = localStorage.getItem('theme');
    const isLight = saved === 'light';
    document.documentElement.setAttribute('data-theme', isLight ? 'light' : 'dark');
    updateToggleButton(isLight);
}

function toggleTheme() {
    const isCurrentlyLight = document.documentElement.getAttribute('data-theme') === 'light';
    const nextTheme = isCurrentlyLight ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', nextTheme);
    localStorage.setItem('theme', nextTheme);
    updateToggleButton(nextTheme === 'light');
}

function updateToggleButton(isLight) {
    if (!themeToggle) return;
    themeToggle.setAttribute('aria-label', isLight ? 'Switch to dark theme' : 'Switch to light theme');
    themeToggle.setAttribute('aria-pressed', String(isLight));
}

// Load course statistics
async function loadCourseStats() {
    try {
        console.log('Loading course stats...');
        const response = await fetch(`${API_URL}/courses`);
        if (!response.ok) throw new Error('Failed to load course stats');
        
        const data = await response.json();
        console.log('Course data received:', data);
        
        // Update stats in UI
        if (totalCourses) {
            totalCourses.textContent = data.total_courses;
        }
        
        // Update course titles
        if (courseTitles) {
            if (data.course_titles && data.course_titles.length > 0) {
                courseTitles.innerHTML = data.course_titles
                    .map(title => `<div class="course-title-item">${title}</div>`)
                    .join('');
            } else {
                courseTitles.innerHTML = '<span class="no-courses">No courses available</span>';
            }
        }
        
    } catch (error) {
        console.error('Error loading course stats:', error);
        // Set default values on error
        if (totalCourses) {
            totalCourses.textContent = '0';
        }
        if (courseTitles) {
            courseTitles.innerHTML = '<span class="error">Failed to load courses</span>';
        }
    }
}

function sendFeedback(rating, query, upBtn, downBtn) {
    upBtn.disabled = true;
    downBtn.disabled = true;
    upBtn.classList.toggle('active', rating > 0);
    downBtn.classList.toggle('active', rating < 0);
    fetch(`${API_URL}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: currentSessionId, rating, query }),
    }).catch(() => {});
}

// Poll /api/metrics/ragas until scores are ready, then update the badge
async function pollRagasScore(badge, attempts = 0) {
    const MAX_ATTEMPTS = 20;
    const INTERVAL_MS = 3000;

    if (attempts >= MAX_ATTEMPTS) {
        badge.className = 'ragas-badge pending';
        badge.textContent = '— RAGAS timeout';
        return;
    }

    try {
        const res = await fetch(`${API_URL}/metrics/ragas`);
        if (!res.ok) throw new Error();
        const data = await res.json();

        if (!data.ready) {
            setTimeout(() => pollRagasScore(badge, attempts + 1), INTERVAL_MS);
            return;
        }

        if (data.faithfulness === null) {
            badge.className = 'ragas-badge pending';
            badge.textContent = '— RAGAS indisponible';
            return;
        }

        const score = data.faithfulness;
        const pct = Math.round(score * 100);
        const level = score >= 0.8 ? 'good' : score >= 0.6 ? 'medium' : 'poor';
        const icon = score >= 0.8 ? '✓' : score >= 0.6 ? '~' : '✗';

        badge.className = `ragas-badge ${level}`;
        badge.textContent = `${icon} fidélité ${pct}%`;
        badge.title = `Faithfulness: ${score} · Relevancy: ${data.relevancy}`;
    } catch {
        setTimeout(() => pollRagasScore(badge, attempts + 1), INTERVAL_MS);
    }
}