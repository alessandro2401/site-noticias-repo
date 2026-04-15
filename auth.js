/**
 * Sistema de Autenticação - Administradora Mutual
 * Acesso restrito aos usuários autorizados.
 */
const AUTHORIZED_USERS = [
    {
        email: 'alessandro@pizzolatto.com.br',
        password: 'Mmb@2026br$',
        name: 'Alessandro Pizzolatto'
    },
    {
        email: 'junio.tosta@alphanacional.com.br',
        password: 'Mmb@2026br$',
        name: 'Junio Tosta'
    },
    {
        email: 'adriele.roque@grupommb.com',
        password: 'Mmb@2026br$',
        name: 'Adriele Roque'
    }
];

const STORAGE_KEY = 'mutual_auth_session';

class AuthManager {
    constructor() {
        this.currentUser = null;
        this.loadSession();
    }

    loadSession() {
        try {
            const sessionData = sessionStorage.getItem(STORAGE_KEY);
            if (sessionData) {
                const session = JSON.parse(sessionData);
                if (session && session.user && session.user.email) {
                    const isAuthorized = AUTHORIZED_USERS.some(
                        u => u.email.toLowerCase() === session.user.email.toLowerCase()
                    );
                    if (isAuthorized) {
                        this.currentUser = session.user;
                        return true;
                    }
                }
            }
            return false;
        } catch (error) {
            return false;
        }
    }

    saveSession(user) {
        try {
            const session = { user: user, timestamp: new Date().toISOString() };
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session));
            this.currentUser = user;
            return true;
        } catch (error) {
            return false;
        }
    }

    login(email, password) {
        const user = AUTHORIZED_USERS.find(u =>
            u.email.toLowerCase() === email.toLowerCase() &&
            u.password === password
        );
        if (user) {
            const userToSave = { email: user.email, name: user.name };
            this.saveSession(userToSave);
            return { success: true, user: userToSave };
        } else {
            return { success: false, message: 'E-mail ou senha incorretos.' };
        }
    }

    logout() {
        sessionStorage.removeItem(STORAGE_KEY);
        this.currentUser = null;
    }

    isAuthenticated() {
        return this.currentUser !== null;
    }

    getCurrentUser() {
        return this.currentUser;
    }

    protectPage() {
        if (!this.isAuthenticated()) {
            // Determina o caminho correto para login.html
            const currentPath = window.location.pathname;
            const depth = (currentPath.match(/\//g) || []).length - 1;
            const prefix = depth > 0 ? '../'.repeat(depth) : '';
            sessionStorage.setItem('redirect_after_login', window.location.href);
            window.location.href = prefix + 'login.html';
            return false;
        }
        return true;
    }

    redirectAfterLogin() {
        const redirectUrl = sessionStorage.getItem('redirect_after_login');
        sessionStorage.removeItem('redirect_after_login');
        if (redirectUrl && redirectUrl.includes(window.location.hostname)) {
            window.location.href = redirectUrl;
        } else {
            window.location.href = 'index.html';
        }
    }
}

const authManager = new AuthManager();
window.authManager = authManager;
