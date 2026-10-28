"""Lojistik kalibrasyon (2 parametre, ridge) ve yardımcılar."""
import numpy as np

def logit(p, eps=1e-4):
    p = np.clip(p, eps, 1 - eps)
    return np.log(p / (1 - p))

def sig(x):
    return 1 / (1 + np.exp(-x))

def lojistik(X, y, ridge, prior, it=30):
    """X (n,d), y (n,), ridge (d,), prior (d,). Newton; ceza = 0.5*sum(ridge*(w-prior)^2)."""
    w = prior.astype(float).copy()
    for _ in range(it):
        z = X @ w
        p = sig(z)
        g = X.T @ (p - y) + ridge * (w - prior)
        H = (X * (p * (1 - p))[:, None]).T @ X + np.diag(ridge)
        dw = np.linalg.solve(H + 1e-9 * np.eye(len(w)), g)
        w -= dw
        if np.abs(dw).max() < 1e-8:
            break
    return w

def kalibre_et(x_egit, y_egit, x_uygula, ridge=2.0):
    """Tek özellikli: logit(p) -> a + b*logit(p)."""
    X = np.column_stack([np.ones(len(x_egit)), x_egit])
    w = lojistik(X, y_egit, np.array([ridge, ridge]), np.array([0.0, 1.0]))
    Xu = np.column_stack([np.ones(len(x_uygula)), x_uygula])
    return sig(Xu @ w), w
