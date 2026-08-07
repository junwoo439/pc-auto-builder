(() => {
    "use strict";

    const pageLabels = {
        "/": "직접 견적",
        "/app": "직접 견적",
        "/recommend": "AI 자동 추천",
        "/admin": "부품 관리",
        "/import": "URL 가져오기",
        "/bulk-import": "대량 수집",
        "/backup": "백업 관리"
    };

    const normalizePath = (href) => {
        try {
            const url = new URL(href, window.location.origin);
            return url.pathname.replace(/\/$/, "") || "/";
        } catch {
            return "";
        }
    };

    const currentPath = window.location.pathname.replace(/\/$/, "") || "/";
    document.body.classList.add("neo-ui");

    document.querySelectorAll("nav a").forEach((link) => {
        const path = normalizePath(link.getAttribute("href") || "");
        const rawText = (link.textContent || "").trim();

        if (pageLabels[path] && (!rawText || rawText.includes("?") || rawText.includes("�"))) {
            link.textContent = pageLabels[path];
        }

        link.classList.remove("highlight");
        if (path === currentPath || (currentPath === "/" && path === "/app")) {
            link.classList.add("neo-active");
            link.setAttribute("aria-current", "page");
        }
    });

    const statusChip = document.createElement("div");
    statusChip.className = "neo-status-chip";
    statusChip.setAttribute("aria-hidden", "true");
    statusChip.innerHTML = '<span class="neo-status-dot"></span><span>LOCAL ENGINE ONLINE</span>';
    document.body.appendChild(statusChip);

    let pointerFrame = 0;
    window.addEventListener("pointermove", (event) => {
        if (pointerFrame) return;
        pointerFrame = window.requestAnimationFrame(() => {
            document.body.style.setProperty("--mx", `${event.clientX}px`);
            document.body.style.setProperty("--my", `${event.clientY}px`);
            pointerFrame = 0;
        });
    }, { passive: true });

    document.querySelectorAll("button").forEach((button) => {
        button.addEventListener("pointerdown", (event) => {
            if (button.disabled) return;
            const rect = button.getBoundingClientRect();
            const ripple = document.createElement("span");
            ripple.className = "neo-ripple";
            ripple.style.left = `${event.clientX - rect.left}px`;
            ripple.style.top = `${event.clientY - rect.top}px`;
            button.appendChild(ripple);
            window.setTimeout(() => ripple.remove(), 650);
        });
    });

    const revealTargets = document.querySelectorAll(".card, .part-card, #result");
    if ("IntersectionObserver" in window) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return;
                entry.target.classList.add("neo-visible");
                observer.unobserve(entry.target);
            });
        }, { threshold: 0.08 });

        revealTargets.forEach((element, index) => {
            element.classList.add("neo-reveal");
            element.style.transitionDelay = `${Math.min(index * 45, 260)}ms`;
            observer.observe(element);
        });
    } else {
        revealTargets.forEach((element) => element.classList.add("neo-visible"));
    }
})();
