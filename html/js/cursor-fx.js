/**
 * AudioHub Cursor Interaction Engine (v2.5)
 * Based on Design System Spec Section 3: Cursor Interaction with Background
 * - Black Gold: Gold Glow follows cursor (250-500ms smooth lerp) + Floating Stardust Particles + Ambient Mesh Shift
 * - Clean Light: Soft Circular Glow follows cursor (200-400ms smooth lerp) + Subtle Expanding Ripple
 */

(function() {
    let canvas, ctx;
    let width, height;
    let mouseX = -1000, mouseY = -1000;
    let cursorX = -1000, cursorY = -1000;
    let isMoving = false;
    let moveTimeout;
    let particles = [];
    let ripples = [];
    let lastSpawn = 0;
    let isGoldTheme = true;

    // Mode options: 'glow', 'particles', 'combined'
    window.cursorFxMode = 'combined';

    function init() {
        // Create canvas if not already present
        canvas = document.getElementById('cursor-bg-canvas');
        if (!canvas) {
            canvas = document.createElement('canvas');
            canvas.id = 'cursor-bg-canvas';
            canvas.style.position = 'fixed';
            canvas.style.top = '0';
            canvas.style.left = '0';
            canvas.style.width = '100vw';
            canvas.style.height = '100vh';
            canvas.style.pointerEvents = 'none';
            canvas.style.zIndex = '25';
            document.body.prepend(canvas);
        }

        ctx = canvas.getContext('2d');
        resize();
        window.addEventListener('resize', resize, { passive: true });

        // Mouse tracking
        window.addEventListener('mousemove', (e) => {
            mouseX = e.clientX;
            mouseY = e.clientY;
            isMoving = true;
            clearTimeout(moveTimeout);
            moveTimeout = setTimeout(() => { isMoving = false; }, 150);

            const now = performance.now();
            if (now - lastSpawn > 35) { // 28-30 particles/sec
                lastSpawn = now;
                spawnEffect(mouseX, mouseY);
            }
        }, { passive: true });

        // Touch handling
        window.addEventListener('touchmove', (e) => {
            if (e.touches.length > 0) {
                mouseX = e.touches[0].clientX;
                mouseY = e.touches[0].clientY;
                isMoving = true;
            }
        }, { passive: true });

        window.addEventListener('mouseleave', () => {
            mouseX = -1000;
            mouseY = -1000;
        });

        checkTheme();
        const observer = new MutationObserver(checkTheme);
        observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });

        requestAnimationFrame(render);
    }

    function checkTheme() {
        const wasGold = isGoldTheme;
        isGoldTheme = document.documentElement.classList.contains('theme-gold') ||
                      document.body.classList.contains('theme-gold');
        if (wasGold !== isGoldTheme) {
            particles = [];
            ripples = [];
        }
    }

    function resize() {
        width = window.innerWidth;
        height = window.innerHeight;
        if (canvas) {
            canvas.width = width * window.devicePixelRatio;
            canvas.height = height * window.devicePixelRatio;
            ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
        }
    }

    function spawnEffect(x, y) {
        if (window.cursorFxMode === 'glow') return;

        if (isGoldTheme) {
            // Spawn 1-2 delicate golden stardust particles
            for (let i = 0; i < 2; i++) {
                particles.push({
                    x: x + (Math.random() - 0.5) * 12,
                    y: y + (Math.random() - 0.5) * 12,
                    vx: (Math.random() - 0.5) * 0.8,
                    vy: (Math.random() - 0.5) * 0.8 - 0.3, // slight upward float
                    size: Math.random() * 2.2 + 1.2,
                    alpha: 0.85,
                    decay: Math.random() * 0.02 + 0.022 // 400-500ms lifespan
                });
            }
        } else {
            // Spawn subtle ripple
            ripples.push({
                x: x,
                y: y,
                radius: 4,
                maxRadius: Math.random() * 25 + 35,
                alpha: 0.22,
                decay: 0.012
            });
        }
    }

    function render() {
        ctx.clearRect(0, 0, width, height);

        // Smooth cursor lerp (250-400ms physical damping)
        if (cursorX === -1000) {
            cursorX = mouseX;
            cursorY = mouseY;
        } else {
            cursorX += (mouseX - cursorX) * 0.12;
            cursorY += (mouseY - cursorY) * 0.12;
        }

        const mode = window.cursorFxMode || 'combined';

        // 1. CURSOR GLOW
        if ((mode === 'glow' || mode === 'combined') && cursorX > -200 && cursorX < width + 200) {
            const glowRadius = isGoldTheme ? 380 : 320;
            const grad = ctx.createRadialGradient(cursorX, cursorY, 0, cursorX, cursorY, glowRadius);

            if (isGoldTheme) {
                // Gold glow: warm, soft, non-intrusive
                grad.addColorStop(0, 'rgba(212, 175, 55, 0.12)');
                grad.addColorStop(0.35, 'rgba(186, 144, 38, 0.045)');
                grad.addColorStop(0.7, 'rgba(140, 106, 18, 0.015)');
                grad.addColorStop(1, 'rgba(0, 0, 0, 0)');
            } else {
                // Clean Light: soft slate circular aura
                grad.addColorStop(0, 'rgba(15, 23, 42, 0.04)');
                grad.addColorStop(0.45, 'rgba(15, 23, 42, 0.012)');
                grad.addColorStop(1, 'rgba(255, 255, 255, 0)');
            }

            ctx.fillStyle = grad;
            ctx.beginPath();
            ctx.arc(cursorX, cursorY, glowRadius, 0, Math.PI * 2);
            ctx.fill();
        }

        // 2. PARTICLES TRAIL (Black Gold)
        if (isGoldTheme && (mode === 'particles' || mode === 'combined')) {
            for (let i = particles.length - 1; i >= 0; i--) {
                const p = particles[i];
                p.x += p.vx;
                p.y += p.vy;
                p.alpha -= p.decay;

                if (p.alpha <= 0) {
                    particles.splice(i, 1);
                    continue;
                }

                ctx.save();
                ctx.shadowColor = 'rgba(245, 217, 122, ' + (p.alpha * 0.8) + ')';
                ctx.shadowBlur = 8;
                ctx.fillStyle = 'rgba(245, 217, 122, ' + p.alpha + ')';
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
                ctx.fill();
                ctx.restore();
            }
        }

        // 3. RIPPLES (Clean Light)
        if (!isGoldTheme && (mode === 'particles' || mode === 'combined')) {
            for (let i = ripples.length - 1; i >= 0; i--) {
                const r = ripples[i];
                r.radius += (r.maxRadius - r.radius) * 0.1;
                r.alpha -= r.decay;

                if (r.alpha <= 0 || r.radius >= r.maxRadius - 1) {
                    ripples.splice(i, 1);
                    continue;
                }

                ctx.strokeStyle = 'rgba(15, 23, 42, ' + r.alpha + ')';
                ctx.lineWidth = 1.2;
                ctx.beginPath();
                ctx.arc(r.x, r.y, r.radius, 0, Math.PI * 2);
                ctx.stroke();
            }
        }

        requestAnimationFrame(render);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
