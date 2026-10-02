// The cut-out genre's procedural visuals: the `mouth` and the `eye` (an#225).
//
// They used to be built into the stage's runtime.js. A genre's runtime script
// registers visual kinds with `window.anRegisterVisual(kind, make)`; the stage
// writes this file into the staged runtime's extensions.js (RuntimeScript
// "cutout_visuals", registered by cutan.genre.CUTOUT) and checks registered kinds
// before its own. The drawing code is byte-for-byte what runtime.js had.
(function () {
    'use strict';
    const PIXI = window.PIXI;

    function parseColor(s) {
        if (typeof s !== 'string') return 0x888888;
        const hex = s.startsWith('#') ? s.slice(1) : s;
        return parseInt(hex.padEnd(6, '0').slice(0, 6), 16);
    }

    function makeEye(visualSpec) {
        // White eye-ball + dark pupil, both ellipses. The compiler stamps
        // visualSpec with width/height for the eye-ball; pupil sizes derive.
        const g = new PIXI.Graphics();
        const w = visualSpec.width || 10;
        const h = visualSpec.height || 8;
        // Eye white
        g.beginFill(0xffffff, 1.0);
        g.lineStyle(0.6, 0x222222, 0.6);
        g.drawEllipse(0, 0, w / 2, h / 2);
        g.endFill();
        // Pupil
        g.lineStyle(0);
        g.beginFill(parseColor(visualSpec.color || '#1a1a1a'), 1.0);
        g.drawEllipse(0, 0, w / 4, h / 3);
        g.endFill();
        return g;
    }

    // Mouth-shape table for viseme rendering. Each entry describes a mouth
    // drawn with two bezier arcs (top & bottom lip). w/h define the bounding
    // box, lipColor outlines, fillColor fills the mouth interior.
    // Mirrors the lookup in an/adapters/cutout/compile.py docstrings.
    const VISEME_SHAPES = {
        // closed: thin line, slight smile
        X: { w: 22, h: 3,  open: 0.0, smile: 0.05 },
        A: { w: 22, h: 4,  open: 0.05, smile: 0.10 },
        // mid open
        B: { w: 22, h: 9,  open: 0.4, smile: 0.0 },
        C: { w: 24, h: 14, open: 0.7, smile: 0.0 },
        D: { w: 26, h: 20, open: 1.0, smile: 0.0 },  // wide open
        // rounded
        E: { w: 20, h: 17, open: 0.85, smile: -0.05 },
        F: { w: 14, h: 14, open: 0.9, smile: -0.10 },  // tight rounded "ooh"
        G: { w: 22, h: 7,  open: 0.2, smile: 0.0, teeth: true },
        H: { w: 18, h: 6,  open: 0.15, smile: 0.0, tongue: true },
    };
    const MOUTH_REST = 'X';
    const _LIP_COLOR  = 0x6b2b2b;
    const _MOUTH_FILL = 0x2a1010;
    const _TEETH_COLOR = 0xfafafa;
    const _TONGUE_COLOR = 0xb04848;

    function drawMouthShape(g, visemeCode) {
        // Loud on an unknown code, like every other bad swap key (an#87).
        // The old `|| VISEME_SHAPES.X` fallback silently drew the closed
        // mouth for typos AND for lowercase codes (the sprite path used to
        // upper-case, this one never did) — the compiler now normalises case
        // at emission and validates codes, so anything unknown arriving here
        // is a hand-written scene's mistake and deserves a diagnosis.
        const s = VISEME_SHAPES[visemeCode];
        if (!s) {
            throw new Error(
                'unknown mouth shape ' + JSON.stringify(visemeCode) +
                '. Known: ' + JSON.stringify(Object.keys(VISEME_SHAPES).sort())
            );
        }
        const w = s.w, h = s.h;
        const halfW = w / 2;
        const halfH = h / 2;
        const smile = (s.smile || 0) * h * 1.5; // pixels of upturn at corners
        g.clear();

        // Build the mouth as a quad-arc lens shape:
        //   top lip:    (-halfW, +smile) → quad → (+halfW, +smile)  with control above
        //   bottom lip: (+halfW, +smile) → quad → (-halfW, +smile)  with control below
        // Mouth-fill inside, outlined in lip color.
        g.lineStyle(1.0, _LIP_COLOR, 1.0);
        g.beginFill(_MOUTH_FILL, 1.0);
        g.moveTo(-halfW, smile);
        // top arc — control point pulled UP by some fraction of openness
        g.quadraticCurveTo(0, -halfH * 0.6 - smile * 0.2, +halfW, smile);
        // bottom arc — control point pushed DOWN by openness amount
        g.quadraticCurveTo(0, +halfH * (0.5 + 0.5 * s.open), -halfW, smile);
        g.endFill();

        if (s.teeth) {
            g.lineStyle(0);
            g.beginFill(_TEETH_COLOR, 1.0);
            g.drawRect(-halfW * 0.7, -1.5, w * 0.7, 2.5);
            g.endFill();
        }
        if (s.tongue) {
            g.lineStyle(0);
            g.beginFill(_TONGUE_COLOR, 1.0);
            g.drawEllipse(0, halfH * 0.2, w * 0.18, h * 0.18);
            g.endFill();
        }
    }

    window.anRegisterVisual('mouth', function (visualSpec) {
        // Procedural drawn mouth, initialized to the rest viseme. Its swap
        // vocabulary is DECLARED on the object (an#87): _anDrawSets maps a set
        // name to the redraw function, so the generic swap path applies `viseme`
        // here the same way it swaps textures on a sprite.
        const g = new PIXI.Graphics();
        drawMouthShape(g, MOUTH_REST);
        g._anDrawSets = {
            viseme: {
                keys: Object.keys(VISEME_SHAPES).sort(),
                apply: drawMouthShape,
                // What it was built showing: the pose a seek to before the first
                // viseme key restores (an#185).
                rest: MOUTH_REST,
            },
        };
        return g;
    });
    window.anRegisterVisual('eye', function (visualSpec) {
        return makeEye(visualSpec);
    });
})();
