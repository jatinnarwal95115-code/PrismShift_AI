(async () => {
  const token = window.PSApi.getToken();
  if (!token) {
    location.replace("login.html");
    return;
  }
  try {
    const result = await window.PSApi.get("/auth/me", { redirectOn401: false });
    if (!result?.user) throw new Error("Invalid user response.");
    localStorage.setItem("prismshift_user", JSON.stringify({
      id: result.user.id, name: result.user.name, email: result.user.email
    }));
    location.replace("dashboard.html");
  } catch (error) {
    window.PSApi.clearSession();
    const message = document.getElementById("entryMessage");
    if (message) message.textContent = "Your session expired or the backend is unavailable. Redirecting to sign in…";
    location.replace("login.html");
  }
})();
