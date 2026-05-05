// js/dragon.js
// Full Three.js dragon scene with orbit controls, lighting, atmosphere, and GLTF loader.
// Place this file at: js/dragon.js
// Requires: assets/models/dragon.glb  (see README for where to download a free model)
//
// HOW TO INCLUDE ON YOUR PAGE — add these tags BEFORE your <script src="js/dragon.js">:
//
//   <script type="importmap">
//   {
//     "imports": {
//       "three":                          "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
//       "three/addons/":                  "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
//     }
//   }
//   </script>
//   <script type="module" src="js/dragon.js"></script>
//
// NOTE: This file must be loaded as type="module" (the importmap above enables that).

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader }    from 'three/addons/loaders/GLTFLoader.js';

// ── Canvas & Renderer ─────────────────────────────────────────────────────────
const canvas = document.getElementById('dragon-canvas');

// Gracefully bail if the canvas element isn't present on this page
if (!canvas) {
  console.info('dragon.js: no #dragon-canvas element found — scene not initialised.');
  throw new Error('dragon.js: canvas not found');  // halts this module only
}

const renderer = new THREE.WebGLRenderer({
  canvas,
  antialias: true,
  alpha:     true,   // transparent bg so your CSS background shows through
});
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(canvas.clientWidth, canvas.clientHeight);
renderer.shadowMap.enabled      = true;
renderer.shadowMap.type         = THREE.PCFSoftShadowMap;
renderer.outputColorSpace       = THREE.SRGBColorSpace;
renderer.toneMapping            = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure    = 1.2;

// ── Scene ─────────────────────────────────────────────────────────────────────
const scene = new THREE.Scene();
scene.fog   = new THREE.FogExp2(0x0a0a0f, 0.08);   // dark exponential fog

// ── Camera ────────────────────────────────────────────────────────────────────
const camera = new THREE.PerspectiveCamera(
  50,
  canvas.clientWidth / canvas.clientHeight,
  0.1,
  100
);
camera.position.set(0, 1.5, 5);

// ── Orbit Controls ────────────────────────────────────────────────────────────
const controls = new OrbitControls(camera, canvas);
controls.enableDamping   = true;
controls.dampingFactor   = 0.05;
controls.enablePan       = false;
controls.minDistance     = 2;
controls.maxDistance     = 10;
controls.minPolarAngle   = Math.PI * 0.1;
controls.maxPolarAngle   = Math.PI * 0.85;
controls.autoRotate      = true;
controls.autoRotateSpeed = 0.6;
controls.target.set(0, 0.5, 0);
controls.update();

// ── Lighting ──────────────────────────────────────────────────────────────────

// Soft ambient base
const ambientLight = new THREE.AmbientLight(0x1a1a2e, 1.5);
scene.add(ambientLight);

// Key light — warm purple from upper-left
const keyLight = new THREE.DirectionalLight(0x9d4edd, 3.5);
keyLight.position.set(-3, 4, 3);
keyLight.castShadow                  = true;
keyLight.shadow.mapSize.set(1024, 1024);
keyLight.shadow.camera.near          = 0.5;
keyLight.shadow.camera.far           = 30;
keyLight.shadow.camera.left          = -5;
keyLight.shadow.camera.right         =  5;
keyLight.shadow.camera.top           =  5;
keyLight.shadow.camera.bottom        = -5;
scene.add(keyLight);

// Rim light — cyan from behind-right (makes edges pop)
const rimLight = new THREE.DirectionalLight(0x00d4ff, 1.5);
rimLight.position.set(4, 2, -4);
scene.add(rimLight);

// Fill light — faint warm orange from below
const fillLight = new THREE.PointLight(0xff6b00, 0.8, 12);
fillLight.position.set(2, -1, 2);
scene.add(fillLight);

// Animated orbit light — circles the dragon like breathing fire
const orbitLight = new THREE.PointLight(0xff3300, 2.0, 6);
scene.add(orbitLight);

// ── Ground Plane (receives shadows) ──────────────────────────────────────────
const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(20, 20),
  new THREE.MeshStandardMaterial({
    color:       0x0a0a0f,
    roughness:   1,
    metalness:   0,
    transparent: true,
    opacity:     0.6,
  })
);
ground.rotation.x  = -Math.PI / 2;
ground.position.y  = -1.2;
ground.receiveShadow = true;
scene.add(ground);

// ── Particle System (floating embers / stars) ─────────────────────────────────
const PARTICLE_COUNT  = 300;
const particleGeo     = new THREE.BufferGeometry();
const positions       = new Float32Array(PARTICLE_COUNT * 3);
const particleSpeeds  = new Float32Array(PARTICLE_COUNT);

for (let i = 0; i < PARTICLE_COUNT; i++) {
  positions[i * 3]     = (Math.random() - 0.5) * 10;
  positions[i * 3 + 1] = (Math.random() - 0.5) * 8;
  positions[i * 3 + 2] = (Math.random() - 0.5) * 10;
  particleSpeeds[i]    = 0.002 + Math.random() * 0.004;
}

particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));

const particles = new THREE.Points(
  particleGeo,
  new THREE.PointsMaterial({
    color:           0xcc44ff,
    size:            0.04,
    sizeAttenuation: true,
    transparent:     true,
    opacity:         0.7,
  })
);
scene.add(particles);

// ── Placeholder (shown until .glb loads) ─────────────────────────────────────
// A glowing icosahedron so the page isn't empty before the model arrives
const placeholder = new THREE.Mesh(
  new THREE.IcosahedronGeometry(1, 1),
  new THREE.MeshStandardMaterial({ color: 0x7c3aed, roughness: 0.2, metalness: 0.8 })
);
placeholder.castShadow = true;
placeholder.position.y = 0.2;
scene.add(placeholder);

// ── GLTF Dragon Loader ────────────────────────────────────────────────────────
let dragonModel = null;
let mixer       = null;   // AnimationMixer for skeletal animations

const loader = new GLTFLoader();

loader.load(
  'assets/models/dragon.glb',

  // onLoad
  (gltf) => {
    dragonModel = gltf.scene;

    // Auto-scale: normalize to ~2.5 units regardless of source size
    const box    = new THREE.Box3().setFromObject(dragonModel);
    const size   = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    const scale  = 2.5 / maxDim;

    dragonModel.scale.setScalar(scale);
    dragonModel.position.sub(center.multiplyScalar(scale));
    dragonModel.position.y += 0.3;

    // Shadows + subtle emissive glow on every mesh
    dragonModel.traverse((child) => {
      if (child.isMesh) {
        child.castShadow    = true;
        child.receiveShadow = true;
        if (child.material) {
          child.material.emissive          = new THREE.Color(0x2d1b69);
          child.material.emissiveIntensity = 0.15;
        }
      }
    });

    // Play any baked animations (wing flaps, idle, etc.)
    if (gltf.animations && gltf.animations.length > 0) {
      mixer = new THREE.AnimationMixer(dragonModel);
      gltf.animations.forEach((clip) => mixer.clipAction(clip).play());
    }

    scene.add(dragonModel);
    scene.remove(placeholder);
    console.log('✅ Dragon model loaded.');
  },

  // onProgress
  (xhr) => {
    if (xhr.total > 0) {
      console.log(`Dragon loading: ${Math.round((xhr.loaded / xhr.total) * 100)}%`);
    }
  },

  // onError — expected until you add the .glb file
  () => {
    console.info('ℹ️ No dragon.glb found — showing placeholder. Drop a .glb into assets/models/ to load the real model.');
    // If a static hero image fallback exists, swap it in
    const heroFallback = document.getElementById('dragon-hero-fallback');
    if (heroFallback) {
      canvas.style.display  = 'none';
      heroFallback.style.display = 'block';
    }
  }
);

// ── Clock ─────────────────────────────────────────────────────────────────────
const clock = new THREE.Clock();

// ── Animation Loop ────────────────────────────────────────────────────────────
function animate() {
  requestAnimationFrame(animate);

  const elapsed = clock.getElapsedTime();
  const delta   = clock.getDelta();

  // Orbit light circles the model like a fire breath effect
  orbitLight.position.set(
    Math.sin(elapsed * 1.2) * 2.5,
    0.5 + Math.sin(elapsed * 0.7) * 0.5,
    Math.cos(elapsed * 1.2) * 2.5
  );
  orbitLight.intensity = 1.5 + Math.sin(elapsed * 3) * 0.8;

  // Gentle bob
  if (dragonModel) {
    dragonModel.position.y = 0.3 + Math.sin(elapsed * 0.8) * 0.08;
  } else {
    placeholder.position.y = 0.2 + Math.sin(elapsed * 0.8) * 0.1;
    placeholder.rotation.y += 0.005;
  }

  // Drift particles upward, wrap at top
  const pos = particleGeo.attributes.position.array;
  for (let i = 0; i < PARTICLE_COUNT; i++) {
    pos[i * 3 + 1] += particleSpeeds[i];
    if (pos[i * 3 + 1] > 4) pos[i * 3 + 1] = -4;
  }
  particleGeo.attributes.position.needsUpdate = true;

  // Skeletal animation
  if (mixer) mixer.update(delta);

  controls.update();
  renderer.render(scene, camera);
}

animate();

// ── Resize Handler ────────────────────────────────────────────────────────────
window.addEventListener('resize', () => {
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  renderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
});
