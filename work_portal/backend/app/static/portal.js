(function () {
    const KEY_STORAGE = "l10_api_key";

    function getKey(forcePrompt) {
        let k = localStorage.getItem(KEY_STORAGE);
        if (!k || forcePrompt) {
            k = window.prompt("Enter portal API key:");
            if (k) localStorage.setItem(KEY_STORAGE, k);
        }
        return k;
    }

    function resetKey() {
        localStorage.removeItem(KEY_STORAGE);
    }

    async function apiRequest(path, options) {
        options = options || {};
        let key = getKey(false);
        if (!key) throw new Error("API key required");
        const headers = Object.assign({ "X-API-Key": key }, options.headers || {});
        if (options.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
        let res = await fetch(path, Object.assign({}, options, { headers }));
        if (res.status === 401) {
            resetKey();
            const retry = getKey(true);
            if (!retry) throw new Error("API key required");
            const headers2 = Object.assign({ "X-API-Key": retry }, options.headers || {});
            if (options.body && !headers2["Content-Type"]) headers2["Content-Type"] = "application/json";
            res = await fetch(path, Object.assign({}, options, { headers: headers2 }));
        }
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res;
    }

    async function handleAction(btn, fn) {
        btn.disabled = true;
        btn.classList.add("is-loading");
        try {
            await fn();
            window.location.reload();
        } catch (err) {
            alert("Failed: " + err.message);
            btn.disabled = false;
            btn.classList.remove("is-loading");
        }
    }

    function wireToggleRock() {
        document.querySelectorAll("button.check[data-rock-id]").forEach(function (btn) {
            btn.addEventListener("click", function () {
                const id = btn.dataset.rockId;
                handleAction(btn, () => apiRequest(`/api/rocks/${encodeURIComponent(id)}/toggle`, { method: "POST" }));
            });
        });
    }

    function wireMoveRock() {
        document.querySelectorAll(".move-rock-btn").forEach(function (btn) {
            btn.addEventListener("click", function () {
                if (!confirm("Move this rock to To-Dos? It will be removed from quarterly rocks.")) return;
                const id = btn.dataset.rockId;
                handleAction(btn, () => apiRequest(`/api/rocks/${encodeURIComponent(id)}/move`, { method: "POST" }));
            });
        });
    }

    function wireToggleAction() {
        document.querySelectorAll("button.check[data-action-id]").forEach(function (btn) {
            btn.addEventListener("click", function () {
                const mid = btn.dataset.meetingId;
                const aid = btn.dataset.actionId;
                handleAction(btn, () => apiRequest(
                    `/api/action/${encodeURIComponent(mid)}/${encodeURIComponent(aid)}/toggle`,
                    { method: "POST" }
                ));
            });
        });
    }

    function wireMoveAction() {
        document.querySelectorAll(".move-action-btn").forEach(function (btn) {
            btn.addEventListener("click", function () {
                const mid = btn.dataset.meetingId;
                const aid = btn.dataset.actionId;
                handleAction(btn, () => apiRequest(
                    `/api/action/${encodeURIComponent(mid)}/${encodeURIComponent(aid)}/move`,
                    { method: "POST" }
                ));
            });
        });
    }

    function wireToggleTodo() {
        document.querySelectorAll("button.check[data-todo-id]").forEach(function (btn) {
            btn.addEventListener("click", function () {
                const id = btn.dataset.todoId;
                handleAction(btn, () => apiRequest(`/api/todos/${encodeURIComponent(id)}/toggle`, { method: "POST" }));
            });
        });
    }

    function wireDeleteTodo() {
        document.querySelectorAll(".delete-todo-btn").forEach(function (btn) {
            btn.addEventListener("click", function () {
                if (!confirm("Delete this to-do?")) return;
                const id = btn.dataset.todoId;
                handleAction(btn, () => apiRequest(`/api/todos/${encodeURIComponent(id)}`, { method: "DELETE" }));
            });
        });
    }

    function toggleForm(formId, openBtnId, cancelBtnId) {
        const form = document.getElementById(formId);
        const openBtn = document.getElementById(openBtnId);
        const cancelBtn = document.getElementById(cancelBtnId);
        if (!form || !openBtn) return;
        openBtn.addEventListener("click", function () {
            form.classList.remove("hidden");
            const first = form.querySelector("input[required], input");
            if (first) first.focus();
        });
        if (cancelBtn) {
            cancelBtn.addEventListener("click", function () {
                form.classList.add("hidden");
                form.reset();
            });
        }
    }

    function wireAddTodo() {
        toggleForm("add-todo-form", "add-todo-open", "add-todo-cancel");
        const form = document.getElementById("add-todo-form");
        if (!form) return;
        form.addEventListener("submit", async function (e) {
            e.preventDefault();
            const data = Object.fromEntries(new FormData(form).entries());
            const submit = form.querySelector("button[type=submit]");
            handleAction(submit, () => apiRequest("/api/todos", {
                method: "POST",
                body: JSON.stringify(data),
            }));
        });
    }

    function wireAddCompanyRock() {
        toggleForm("add-company-rock-form", "add-company-rock-open", "add-company-rock-cancel");
        const form = document.getElementById("add-company-rock-form");
        if (!form) return;
        form.addEventListener("submit", async function (e) {
            e.preventDefault();
            const data = Object.fromEntries(new FormData(form).entries());
            const submit = form.querySelector("button[type=submit]");
            handleAction(submit, () => apiRequest("/api/company_rocks/add", {
                method: "POST",
                body: JSON.stringify(data),
            }));
        });
    }

    function wireAddPersonRock() {
        document.querySelectorAll(".add-rock-btn").forEach(function (btn) {
            btn.addEventListener("click", function () {
                const card = btn.closest(".person-card");
                if (!card) return;
                const form = card.querySelector(".add-rock-form");
                if (!form) return;
                form.classList.remove("hidden");
                const first = form.querySelector("input[required], input");
                if (first) first.focus();
            });
        });
        document.querySelectorAll(".cancel-add-rock").forEach(function (btn) {
            btn.addEventListener("click", function () {
                const form = btn.closest(".add-rock-form");
                if (form) { form.classList.add("hidden"); form.reset(); }
            });
        });
        document.querySelectorAll(".add-rock-form").forEach(function (form) {
            form.addEventListener("submit", async function (e) {
                e.preventDefault();
                const owner = form.dataset.owner;
                const category = form.dataset.category;
                const data = Object.fromEntries(new FormData(form).entries());
                data.category = category;
                const submit = form.querySelector("button[type=submit]");
                handleAction(submit, () => apiRequest(`/api/rocks/${encodeURIComponent(owner)}/add`, {
                    method: "POST",
                    body: JSON.stringify(data),
                }));
            });
        });
    }

    function wireResetKey() {
        const resetBtn = document.getElementById("reset-key-btn");
        if (resetBtn) {
            resetBtn.addEventListener("click", function () {
                resetKey();
                alert("Portal API key cleared — you'll be asked again on next action.");
            });
        }
    }

    document.addEventListener("DOMContentLoaded", function () {
        wireToggleRock();
        wireMoveRock();
        wireToggleAction();
        wireMoveAction();
        wireToggleTodo();
        wireDeleteTodo();
        wireAddTodo();
        wireAddCompanyRock();
        wireAddPersonRock();
        wireResetKey();
    });
})();
