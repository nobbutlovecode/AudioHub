/**
 * AudioHub Cursor Interaction Engine (v2.6)
 * - Black Gold: Gold Glow follows cursor + Floating Stardust Particles
 * - Clean Light: Google Antigravity Interactive Colorful Particle Field (Red/Cyan/Violet/Amber Capsule Dashes & Fluid Repulsion)
 */

(function() {
    let canvas, ctx;
    let width, height;
    let mouseX = -1000, mouseY = -1000;
    let cursorX = -1000, cursorY = -1000;
    let isMoving = false;
    let moveTimeout;
    let particles = [];
    let antigravityParticles = [];
    let lastSpawn = 0;
    let isGoldTheme = false;

    // Palette matching Google Antigravity Clean Light landing page
    const antigravityColors = [
        '#E05D52', // Warm coral red
        '#EA4335', // Google Red
        '#E8715A', // Coral
        '#F49342', // Warm amber
        '#4285F4', // Google Blue
        '#38BDF8', // Cyan / Sky Blue
        '#6366F1', // Indigo
        '#8B5CF6', // Violet
        '#A855F7', // Purple
        '#EC4899', // Pink
        '#94A3B8'  // Subtle slate dot
    ];

    window.cursorFxMode = 'combined';

    function init() {
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

        window.addEventListener('mousemove', (e) => {
            mouseX = e.clientX;
            mouseY = e.clientY;
            isMoving = true;
            clearTimeout(moveTimeout);
            moveTimeout = setTimeout(() => { isMoving = false; }, 150);

            const now = performance.now();
            if (now - lastSpawn > 35) {
                lastSpawn = now;
                spawnGoldParticles(mouseX, mouseY);
            }
        }, { passive: true });

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

        initAntigravityField();
        requestAnimationFrame(render);
    }

    function checkTheme() {
        const wasGold = isGoldTheme;
        isGoldTheme = document.documentElement.classList.contains('theme-gold') ||
                      document.body.classList.contains('theme-gold') ||
                      document.documentElement.classList.contains('liquid-obsidian');
        if (wasGold !== isGoldTheme) {
            particles = [];
        }
    }

    function resize() {
        width = window.innerWidth;
        height = window.innerHeight;
        if (canvas) {
            const dpr = window.devicePixelRatio || 1;
            canvas.width = width * dpr;
            canvas.height = height * dpr;
            ctx.scale(dpr, dpr);
        }
        initAntigravityField();
    }

    function initAntigravityField() {
        antigravityParticles = [];
        const count = 180;
        for (let i = 0; i < count; i++) {
            const x = Math.random() * (width || window.innerWidth);
            const y = Math.random() * (height || window.innerHeight);
            antigravityParticles.push({
                x: x,
                y: y,
                originX: x,
                originY: y,
                length: Math.random() * 5 + 3,
                thickness: Math.random() * 2 + 1.2,
                angle: (Math.random() - 0.5) * 0.8 - Math.PI / 4,
                color: antigravityColors[Math.floor(Math.random() * antigravityColors.length)],
                alpha: Math.random() * 0.45 + 0.45,
                vx: (Math.random() - 0.5) * 0.35,
                vy: (Math.random() - 0.5) * 0.35,
                offsetX: 0,
                offsetY: 0,
                offsetVx: 0,
                offsetVy: 0,
                currentAngle: 0
            });
        }
    }

    function spawnGoldParticles(x, y) {
        if (!isGoldTheme) return;
        if (window.cursorFxMode === 'glow') return;
        for (let i = 0; i < 2; i++) {
            particles.push({
                x: x + (Math.random() - 0.5) * 12,
                y: y + (Math.random() - 0.5) * 12,
                vx: (Math.random() - 0.5) * 0.8,
                vy: (Math.random() - 0.5) * 0.8 - 0.3,
                size: Math.random() * 2.2 + 1.2,
                alpha: 0.85,
                decay: Math.random() * 0.02 + 0.022
            });
        }
    }

    function render() {
        ctx.clearRect(0, 0, width, height);

        if (cursorX === -1000) {
            cursorX = mouseX;
            cursorY = mouseY;
        } else {
            cursorX += (mouseX - cursorX) * 0.12;
            cursorY += (mouseY - cursorY) * 0.12;
        }

        const mode = window.cursorFxMode || 'combined';

        // 1. CURSOR GLOW FOR GOLD THEME
        if (isGoldTheme && (mode === 'glow' || mode === 'combined') && cursorX > -200 && cursorX < width + 200) {
            const glowRadius = 380;
            const grad = ctx.createRadialGradient(cursorX, cursorY, 0, cursorX, cursorY, glowRadius);
            grad.addColorStop(0, 'rgba(212, 175, 55, 0.12)');
            grad.addColorStop(0.35, 'rgba(186, 144, 38, 0.045)');
            grad.addColorStop(0.7, 'rgba(140, 106, 18, 0.015)');
            grad.addColorStop(1, 'rgba(0, 0, 0, 0)');

            ctx.fillStyle = grad;
            ctx.beginPath();
            ctx.arc(cursorX, cursorY, glowRadius, 0, Math.PI * 2);
            ctx.fill();
        }

        // 2. GOLD PARTICLES TRAIL
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

        // 3. CLEAN LIGHT: GOOGLE ANTIGRAVITY PARTICLE FIELD WITH CURSOR REPULSION
        if (!isGoldTheme) {
            const influenceRadius = 160;
            for (let i = 0; i < antigravityParticles.length; i++) {
                const p = antigravityParticles[i];
                p.originX += p.vx;
                p.originY += p.vy;

                if (p.originX < -20) p.originX = width + 20;
                if (p.originX > width + 20) p.originX = -20;
                if (p.originY < -20) p.originY = height + 20;
                if (p.originY > height + 20) p.originY = -20;

                const dx = (p.originX + p.offsetX) - cursorX;
                const dy = (p.originY + p.offsetY) - cursorY;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < influenceRadius && dist > 0.001) {
                    const force = (1 - dist / influenceRadius);
                    const pushPower = force * 6.5;
                    const angle = Math.atan2(dy, dx);
                    p.offsetVx += Math.cos(angle) * pushPower;
                    p.offsetVy += Math.sin(angle) * pushPower;
                    p.currentAngle = angle;
                } else {
                    p.currentAngle = p.angle;
                }

                p.offsetX += p.offsetVx;
                p.offsetY += p.offsetVy;
                p.offsetVx *= 0.88;
                p.offsetVy *= 0.88;
                p.offsetX *= 0.92;
                p.offsetY *= 0.92;

                const posX = p.originX + p.offsetX;
                const posY = p.originY + p.offsetY;

                ctx.save();
                ctx.translate(posX, posY);
                ctx.rotate(p.currentAngle || p.angle);
                ctx.globalAlpha = p.alpha;
                ctx.fillStyle = p.color;

                ctx.beginPath();
                const r = p.thickness / 2;
                const l = p.length;
                ctx.arc(-l / 2 + r, 0, r, Math.PI / 2, Math.PI * 1.5);
                ctx.arc(l / 2 - r, 0, r, -Math.PI / 2, Math.PI / 2);
                ctx.closePath();
                ctx.fill();

                ctx.restore();
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
