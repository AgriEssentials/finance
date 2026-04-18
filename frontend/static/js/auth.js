"use strict";
/**
 * Authentication System for Quant Terminal
 * Handles login, register, and session management
 */

const AUTH_CONFIG = {
    STORAGE_KEY: 'quant_terminal_user',
    SESSION_DURATION: 24 * 60 * 60 * 1000, // 24 hours
};

// DOM Elements
const elements = {
    loginForm: document.getElementById('login-form'),
    registerForm: document.getElementById('register-form'),
    authTabs: document.querySelectorAll('.auth-tab'),
    togglePasswordBtns: document.querySelectorAll('.toggle-password'),
};

// State
let currentUser = null;

/**
 * Initialize auth system
 */
function initAuth() {
    setupEventListeners();
    checkExistingSession();
}

/**
 * Setup all event listeners
 */
function setupEventListeners() {
    // Tab switching
    elements.authTabs.forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });

    // Toggle password visibility
    elements.togglePasswordBtns.forEach(btn => {
        btn.addEventListener('click', () => togglePassword(btn.dataset.target));
    });

    // Form submissions
    if (elements.loginForm) {
        elements.loginForm.addEventListener('submit', handleLogin);
    }
    if (elements.registerForm) {
        elements.registerForm.addEventListener('submit', handleRegister);
    }
}

/**
 * Switch between login and register tabs
 */
function switchTab(tab) {
    // Update tabs
    elements.authTabs.forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
    
    // Update forms
    document.querySelectorAll('.auth-form').forEach(form => {
        form.classList.toggle('active', form.id === `${tab}-form`);
    });
}

/**
 * Toggle password input visibility
 */
function togglePassword(targetId) {
    const input = document.getElementById(targetId);
    if (input) {
        input.type = input.type === 'password' ? 'text' : 'password';
    }
}

/**
 * Handle login form submission
 */
async function handleLogin(e) {
    e.preventDefault();
    
    const email = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;
    const rememberMe = document.getElementById('remember-me').checked;
    
    if (!validateEmail(email)) {
        showToast('Please enter a valid email address', 'error');
        return;
    }
    
    if (!password) {
        showToast('Please enter your password', 'error');
        return;
    }
    
    setLoading(true, 'login-form');
    
    try {
        // Call real backend API
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: email,
                password: password
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Login failed');
        }

        const data = await response.json();

        // Create user object with token
        const user = {
            email,
            name: email.split('@')[0],
            loginTime: Date.now(),
            rememberMe,
            access_token: data.access_token,
            token_type: data.token_type || 'bearer'
        };
        
        // Store session
        storeSession(user, rememberMe);
        
        // Store token for API requests
        localStorage.setItem('access_token', data.access_token);

        showToast('Login successful! Redirecting...', 'success');
        
        // Redirect to analysis page
        setTimeout(() => {
            window.location.href = '/analysis.html';
        }, 1000);
        
    } catch (error) {
        console.error('Login error:', error);
        showToast(error.message || 'Invalid credentials. Please try again.', 'error');
    } finally {
        setLoading(false, 'login-form');
    }
}

/**
 * Handle register form submission
 */
async function handleRegister(e) {
    e.preventDefault();
    
    const name = document.getElementById('register-name').value.trim();
    const email = document.getElementById('register-email').value.trim();
    const password = document.getElementById('register-password').value;
    const confirm = document.getElementById('register-confirm').value;
    const agreeTerms = document.getElementById('agree-terms').checked;
    
    // Validation
    if (!name) {
        showToast('Please enter your full name', 'error');
        return;
    }
    
    if (!validateEmail(email)) {
        showToast('Please enter a valid email address', 'error');
        return;
    }
    
    if (password.length < 8) {
        showToast('Password must be at least 8 characters', 'error');
        return;
    }
    
    if (password !== confirm) {
        showToast('Passwords do not match', 'error');
        return;
    }
    
    if (!agreeTerms) {
        showToast('Please agree to the terms of service', 'error');
        return;
    }
    
    setLoading(true, 'register-form');
    
    try {
        // Call real backend API
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: email,
                email: email,
                password: password,
                full_name: name
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Registration failed');
        }

        const data = await response.json();

        showToast('Account created successfully! Logging you in...', 'success');

        // Create user object
        const user = {
            email,
            name,
            loginTime: Date.now(),
            rememberMe: false
        };
        
        // Store session
        storeSession(user, false);
        
        // Redirect to analysis page
        setTimeout(() => {
            window.location.href = '/analysis.html';
        }, 1000);
        
    } catch (error) {
        console.error('Register error:', error);
        showToast(error.message || 'Registration failed. Please try again.', 'error');
    } finally {
        setLoading(false, 'register-form');
    }
}

/**
 * Validate email format
 */
function validateEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

/**
 * Simulate authentication API call
 */
function simulateAuthAPI() {
    return new Promise((resolve) => {
        setTimeout(resolve, 1500); // Simulate network delay
    });
}

/**
 * Store user session
 */
function storeSession(user, rememberMe) {
    const session = {
        user,
        expires: rememberMe ? Date.now() + AUTH_CONFIG.SESSION_DURATION : null
    };
    
    if (rememberMe) {
        localStorage.setItem(AUTH_CONFIG.STORAGE_KEY, JSON.stringify(session));
    } else {
        sessionStorage.setItem(AUTH_CONFIG.STORAGE_KEY, JSON.stringify(session));
    }
    
    currentUser = user;
}

/**
 * Check for existing session
 */
function checkExistingSession() {
    // Check sessionStorage first (current session)
    let session = sessionStorage.getItem(AUTH_CONFIG.STORAGE_KEY);
    
    // If not found, check localStorage (remember me)
    if (!session) {
        session = localStorage.getItem(AUTH_CONFIG.STORAGE_KEY);
    }
    
    if (session) {
        try {
            const parsed = JSON.parse(session);
            
            // Check if session is expired
            if (parsed.expires && Date.now() > parsed.expires) {
                clearSession();
                return;
            }
            
            currentUser = parsed.user;
            
            // If user is already logged in and on auth page, redirect to analysis
            if (window.location.pathname.includes('auth.html')) {
                window.location.href = '/analysis.html';
            }
        } catch (e) {
            clearSession();
        }
    }
}

/**
 * Get current user
 */
function getCurrentUser() {
    return currentUser;
}

/**
 * Check if user is authenticated
 */
function isAuthenticated() {
    return currentUser !== null;
}

/**
 * Clear user session (logout)
 */
function clearSession() {
    localStorage.removeItem(AUTH_CONFIG.STORAGE_KEY);
    sessionStorage.removeItem(AUTH_CONFIG.STORAGE_KEY);
    currentUser = null;
}

/**
 * Logout user
 */
function logout() {
    clearSession();
    showToast('Logged out successfully', 'success');
    setTimeout(() => {
        window.location.href = '/';
    }, 500);
}

/**
 * Set loading state on button
 */
function setLoading(loading, formId) {
    const form = document.getElementById(formId);
    const btn = form.querySelector('.auth-btn');
    const btnText = btn.querySelector('.btn-text');
    const btnLoader = btn.querySelector('.btn-loader');
    
    btn.disabled = loading;
    btnText.style.display = loading ? 'none' : 'block';
    btnLoader.style.display = loading ? 'block' : 'none';
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    // Remove existing toast
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }
    
    // Create toast
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}</span>
        <span>${message}</span>
    `;
    
    document.body.appendChild(toast);
    
    // Remove after 5 seconds
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

/**
 * Require authentication - redirect to auth if not logged in
 */
function requireAuth() {
    if (!isAuthenticated()) {
        // Store the intended destination
        sessionStorage.setItem('auth_redirect', window.location.pathname);
        window.location.href = '/auth.html';
        return false;
    }
    return true;
}

/**
 * Initialize on page load
 */
document.addEventListener('DOMContentLoaded', initAuth);

// Export functions for use in other scripts
window.AuthSystem = {
    getCurrentUser,
    isAuthenticated,
    logout,
    requireAuth,
    showToast
};
