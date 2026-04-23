"use strict";
/**
 * Authentication System for Quant Terminal - Supabase Edition v2
 * Uses Supabase Auth exclusively - no SQLite fallback
 * Updated: 2026-04-22
 */

console.log('[AUTH] Loading Supabase Auth module v2');

const AUTH_CONFIG = {
    STORAGE_KEY: 'quant_terminal_user',
    TOKEN_KEY: 'access_token',
    REFRESH_KEY: 'refresh_token',
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
    const btn = document.querySelector(`.toggle-password[data-target="${targetId}"]`);
    if (input) {
        const isPassword = input.type === 'password';
        input.type = isPassword ? 'text' : 'password';
        // Update button icon
        if (btn) {
            btn.textContent = isPassword ? '🙈' : '👁';
        }
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
        // Call backend API which uses Supabase Auth
        const requestBody = {
            email: email,
            password: password
        };
        console.log('Login request:', requestBody);
        
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });

        console.log('Login response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Login error response:', errorText);
            let errorMessage = 'Login failed';
            try {
                const errorData = JSON.parse(errorText);
                // Handle different error formats
                if (errorData.detail) {
                    if (typeof errorData.detail === 'string') {
                        errorMessage = errorData.detail;
                    } else if (Array.isArray(errorData.detail)) {
                        // Validation errors array
                        errorMessage = errorData.detail.map(e => e.msg || e.message || JSON.stringify(e)).join(', ');
                    } else {
                        errorMessage = JSON.stringify(errorData.detail);
                    }
                } else if (errorData.message) {
                    errorMessage = errorData.message;
                } else {
                    errorMessage = JSON.stringify(errorData);
                }
            } catch(e) {
                errorMessage = errorText || 'Login failed';
            }
            throw new Error(errorMessage);
        }

        const data = await response.json();

        // Create user object with Supabase tokens
        const user = {
            id: data.user.id,
            email: data.user.email,
            name: data.user.full_name || email.split('@')[0],
            loginTime: Date.now(),
            rememberMe,
            access_token: data.access_token,
            refresh_token: data.refresh_token,
            token_type: data.token_type || 'bearer',
            expires_in: data.expires_in
        };
        
        // Store session
        storeSession(user, rememberMe);
        
        // Store tokens for API requests
        localStorage.setItem(AUTH_CONFIG.TOKEN_KEY, data.access_token);
        localStorage.setItem(AUTH_CONFIG.REFRESH_KEY, data.refresh_token);

        showToast('Login successful! Redirecting...', 'success');
        
        // Check if user has already completed setup (localStorage flag for quick check)
        const setupCompleted = localStorage.getItem('portfolio_setup_completed');
        if (setupCompleted === 'true') {
            console.log('[AUTH] Setup already completed (localStorage), going to dashboard');
            setTimeout(() => {
                window.location.href = '/dashboard.html';
            }, 1000);
            return;
        }
        
        // Check if user needs portfolio setup (only for first-time users)
        try {
            const setupCheck = await fetch('/api/portfolio/setup', {
                headers: { 'Authorization': `Bearer ${data.access_token}` }
            });
            
            if (setupCheck.ok) {
                const setupData = await setupCheck.json();
                console.log('[AUTH] Setup check response:', setupData);
                
                // IMPORTANT: Only check setup_complete flag, NOT cash_balance
                // New users get default cash of 10L but setup_complete is false until they explicitly set up
                setTimeout(() => {
                    if (setupData.setup_complete === true) {
                        console.log('[AUTH] User has completed setup, going to dashboard');
                        // Mark as completed in localStorage to prevent future setup redirects
                        localStorage.setItem('portfolio_setup_completed', 'true');
                        window.location.href = '/dashboard.html';
                    } else {
                        console.log('[AUTH] New user needs setup, redirecting to setup page');
                        window.location.href = '/setup.html';
                    }
                }, 1000);
            } else {
                // If API fails, assume new user and go to setup
                console.log('[AUTH] Setup check failed, assuming new user - going to setup');
                setTimeout(() => {
                    window.location.href = '/setup.html';
                }, 1000);
            }
        } catch (e) {
            // On error, assume new user and go to setup
            console.log('[AUTH] Setup check error, assuming new user:', e);
            setTimeout(() => {
                window.location.href = '/setup.html';
            }, 1000);
        }
        
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
        // Call backend API to register with Supabase Auth
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: email,
                password: password,
                full_name: name
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Register error response:', errorText);
            let errorMessage = 'Registration failed';
            try {
                const errorData = JSON.parse(errorText);
                if (errorData.detail) {
                    if (typeof errorData.detail === 'string') {
                        errorMessage = errorData.detail;
                    } else if (Array.isArray(errorData.detail)) {
                        errorMessage = errorData.detail.map(e => e.msg || e.message || JSON.stringify(e)).join(', ');
                    } else {
                        errorMessage = JSON.stringify(errorData.detail);
                    }
                } else if (errorData.message) {
                    errorMessage = errorData.message;
                } else {
                    errorMessage = JSON.stringify(errorData);
                }
            } catch(e) {
                errorMessage = errorText || 'Registration failed';
            }
            throw new Error(errorMessage);
        }

        const userData = await response.json();
        console.log('Registration successful:', userData);

        showToast('Account created successfully! Logging you in...', 'success');

        // Now auto-login the user
        const loginResponse = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: email,
                password: password
            })
        });

        if (!loginResponse.ok) {
            // If auto-login fails, redirect to login page
            showToast('Registration successful! Please log in.', 'success');
            setTimeout(() => {
                switchTab('login');
                document.getElementById('login-email').value = email;
            }, 1500);
            return;
        }

        const loginData = await loginResponse.json();

        // Create user object with Supabase tokens
        const user = {
            id: loginData.user.id,
            email: loginData.user.email,
            name: loginData.user.full_name || name,
            loginTime: Date.now(),
            rememberMe: false,
            access_token: loginData.access_token,
            refresh_token: loginData.refresh_token,
            token_type: loginData.token_type || 'bearer',
            expires_in: loginData.expires_in
        };

        // Store session
        storeSession(user, false);

        // Store tokens for API requests
        localStorage.setItem(AUTH_CONFIG.TOKEN_KEY, loginData.access_token);
        localStorage.setItem(AUTH_CONFIG.REFRESH_KEY, loginData.refresh_token);

        // Redirect to setup page for onboarding
        setTimeout(() => {
            window.location.href = '/setup.html';
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

            // Restore tokens from user object or localStorage
            if (currentUser && currentUser.access_token) {
                localStorage.setItem(AUTH_CONFIG.TOKEN_KEY, currentUser.access_token);
            }
            if (currentUser && currentUser.refresh_token) {
                localStorage.setItem(AUTH_CONFIG.REFRESH_KEY, currentUser.refresh_token);
            }

            // If user is already logged in and on auth page, check setup status first
            if (window.location.pathname.includes('auth.html')) {
                checkSetupAndRedirect();
            }
        } catch (e) {
            console.error('Session parsing error:', e);
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
    return currentUser !== null && localStorage.getItem(AUTH_CONFIG.TOKEN_KEY) !== null;
}

/**
 * Clear user session (logout)
 */
function clearSession() {
    localStorage.removeItem(AUTH_CONFIG.STORAGE_KEY);
    localStorage.removeItem(AUTH_CONFIG.TOKEN_KEY);
    localStorage.removeItem(AUTH_CONFIG.REFRESH_KEY);
    localStorage.removeItem('portfolio_setup_completed');
    localStorage.removeItem('user_portfolio_setup');
    localStorage.removeItem('user_risk_tolerance');
    localStorage.removeItem('user_preferred_strategy');
    sessionStorage.removeItem(AUTH_CONFIG.STORAGE_KEY);
    currentUser = null;
}

/**
 * Check portfolio setup status and redirect accordingly
 * Only redirects to setup if user hasn't completed portfolio setup
 */
async function checkSetupAndRedirect() {
    const token = localStorage.getItem(AUTH_CONFIG.TOKEN_KEY);
    if (!token) {
        // No token, stay on auth page
        return;
    }
    
    try {
        const response = await fetch('/api/portfolio/setup', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            
            // Check if there's a stored redirect
            const storedRedirect = sessionStorage.getItem('auth_redirect');
            if (storedRedirect) {
                sessionStorage.removeItem('auth_redirect');
                window.location.href = storedRedirect;
                return;
            }
            
            // Only check setup_complete flag - new users get default cash but setup_complete is false
            if (data.setup_complete === true) {
                window.location.href = '/dashboard.html';
            } else {
                window.location.href = '/setup.html';
            }
        } else {
            // API error, assume new user and go to setup
            window.location.href = '/setup.html';
        }
    } catch (error) {
        console.error('Error checking setup status:', error);
        // On error, assume new user and go to setup
        window.location.href = '/setup.html';
    }
}

/**
 * Logout user
 */
async function logout() {
    try {
        // Call backend logout endpoint
        const token = localStorage.getItem(AUTH_CONFIG.TOKEN_KEY);
        if (token) {
            await fetch('/api/auth/logout', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
        }
    } catch (e) {
        console.warn('Logout API call failed:', e);
    }
    
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
 * Make authenticated API request
 * Automatically adds Authorization header if token is available
 */
async function authenticatedFetch(url, options = {}) {
    const token = localStorage.getItem(AUTH_CONFIG.TOKEN_KEY);

    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            ...(token && { 'Authorization': `Bearer ${token}` })
        }
    };

    const mergedOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    };

    try {
        const response = await fetch(url, mergedOptions);

        // Handle 401 Unauthorized - token expired or invalid
        if (response.status === 401) {
            console.warn('Authentication expired. Attempting refresh...');
            
            // Try to refresh token
            const refreshToken = localStorage.getItem(AUTH_CONFIG.REFRESH_KEY);
            if (refreshToken) {
                try {
                    const refreshResponse = await fetch('/api/auth/refresh', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ refresh_token: refreshToken })
                    });
                    
                    if (refreshResponse.ok) {
                        const refreshData = await refreshResponse.json();
                        localStorage.setItem(AUTH_CONFIG.TOKEN_KEY, refreshData.access_token);
                        localStorage.setItem(AUTH_CONFIG.REFRESH_KEY, refreshData.refresh_token);
                        
                        // Retry the original request with new token
                        mergedOptions.headers['Authorization'] = `Bearer ${refreshData.access_token}`;
                        return await fetch(url, mergedOptions);
                    }
                } catch (refreshError) {
                    console.error('Token refresh failed:', refreshError);
                }
            }
            
            // If refresh failed, redirect to login
            clearSession();
            sessionStorage.setItem('auth_redirect', window.location.pathname);
            window.location.href = '/auth.html';
            throw new Error('Session expired. Please log in again.');
        }

        return response;
    } catch (error) {
        console.error('Authenticated fetch error:', error);
        throw error;
    }
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
    showToast,
    authenticatedFetch,
    clearSession
};
