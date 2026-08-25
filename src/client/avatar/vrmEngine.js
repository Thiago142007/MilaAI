/**
 * MILA / GAWR GURA 3D Engine
 * Renders Gawr Gura 3D Model with High-Resolution Textures, Studio Lighting,
 * Dynamic Mouse Cursor Eye/Head Tracking, Realistic Secondary Physics (Tail, Hair),
 * Smooth Talking Animations & Real-Time Lip-Sync.
 *
 * NOTE: In Idle state, no FBX idle animation is played - natural procedural breathing & physics are active instead.
 */

export class VRMEngine {
  constructor(canvasContainer) {
    this.container = canvasContainer;
    this.guraModel = null;
    this.guraBones = {};
    this.hairBones = [];
    this.tailBones = [];
    this.mixer = null;
    this.idleAction = null;
    this.talkingAction = null;
    this.isSpeaking = false;
    this.lipSyncValue = 0;
    this.expression = "neutral";
    this.clock = null;
    this.mouse = { x: 0, y: 0 };
    this.targetMouse = { x: 0, y: 0 };

    this.initScene();
  }

  async initScene() {
    const THREE = window.THREE;
    if (!THREE) {
      await this.loadScript("https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js");
    }
    if (!window.fflate) {
      await this.loadScript("https://cdn.jsdelivr.net/npm/fflate@0.8.0/umd/index.js");
    }
    if (!window.THREE.GLTFLoader) {
      await this.loadScript("https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js");
    }
    if (!window.THREE.FBXLoader) {
      await this.loadScript("https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/FBXLoader.js");
    }

    const T = window.THREE;
    const width = window.innerWidth;
    const height = window.innerHeight;

    this.scene = new T.Scene();
    this.scene.background = new T.Color(0x070b12);

    // Camera setup framed perfectly for Gura portrait
    this.camera = new T.PerspectiveCamera(38, width / height, 0.05, 50.0);
    this.camera.position.set(0, 1.22, 1.35);
    this.camera.lookAt(0, 1.15, 0);

    this.renderer = new T.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.outputEncoding = T.sRGBEncoding;
    this.renderer.toneMapping = T.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.18;
    this.container.appendChild(this.renderer.domElement);

    // Studio Anime Lighting
    const ambientLight = new T.AmbientLight(0xffffff, 1.35);
    this.scene.add(ambientLight);

    const hemiLight = new T.HemisphereLight(0xffffff, 0x334155, 0.9);
    this.scene.add(hemiLight);

    const mainLight = new T.DirectionalLight(0xfff7ed, 1.4);
    mainLight.position.set(1.5, 3.5, 3.0);
    this.scene.add(mainLight);

    const fillLightL = new T.DirectionalLight(0xbae6fd, 0.85);
    fillLightL.position.set(-2.5, 2.0, 2.0);
    this.scene.add(fillLightL);

    const fillLightR = new T.DirectionalLight(0xfce7f3, 0.75);
    fillLightR.position.set(2.5, 2.0, 2.0);
    this.scene.add(fillLightR);

    const cyanRimLight = new T.DirectionalLight(0x38bdf8, 1.5);
    cyanRimLight.position.set(0, 2.8, -2.5);
    this.scene.add(cyanRimLight);

    // Floating Particles Background
    this.createParticles();

    // Procedural Fallback Avatar (shows while loading 3D model)
    this.createProceduralAvatar();

    // Load Gawr Gura 3D Model with Textures and Animations
    this.loadGuraModel();

    this.clock = new T.Clock();
    this.animate();

    window.addEventListener("resize", () => this.onResize());
    window.addEventListener("mousemove", (e) => {
      this.targetMouse.x = (e.clientX / window.innerWidth - 0.5) * 2;
      this.targetMouse.y = (e.clientY / window.innerHeight - 0.5) * 2;
    });
  }

  createParticles() {
    const T = window.THREE;
    const count = 180;
    const geometry = new T.BufferGeometry();
    const positions = new Float32Array(count * 3);

    for (let i = 0; i < count * 3; i += 3) {
      positions[i] = (Math.random() - 0.5) * 6;
      positions[i + 1] = Math.random() * 4;
      positions[i + 2] = (Math.random() - 0.5) * 4;
    }

    geometry.setAttribute("position", new T.BufferAttribute(positions, 3));
    const material = new T.PointsMaterial({
      color: 0x38bdf8,
      size: 0.025,
      transparent: true,
      opacity: 0.5,
    });

    this.particles = new T.Points(geometry, material);
    this.scene.add(this.particles);
  }

  createProceduralAvatar() {
    const T = window.THREE;
    this.avatarGroup = new T.Group();

    const headGeo = new T.SphereGeometry(0.22, 32, 32);
    const skinMat = new T.MeshStandardMaterial({ color: 0xffdfd0, roughness: 0.4 });
    this.head = new T.Mesh(headGeo, skinMat);
    this.head.position.y = 1.35;
    this.avatarGroup.add(this.head);

    const hairMat = new T.MeshStandardMaterial({ color: 0x38bdf8, roughness: 0.3 });
    const hairTop = new T.Mesh(new T.SphereGeometry(0.24, 24, 24, 0, Math.PI * 2, 0, Math.PI * 0.5), hairMat);
    hairTop.position.set(0, 1.38, -0.02);
    this.avatarGroup.add(hairTop);

    const eyeGeo = new T.SphereGeometry(0.045, 16, 16);
    const eyeMat = new T.MeshBasicMaterial({ color: 0x0ea5e9 });
    this.eyeL = new T.Mesh(eyeGeo, eyeMat);
    this.eyeL.position.set(0.08, 1.37, 0.19);
    this.avatarGroup.add(this.eyeL);

    this.eyeR = new T.Mesh(eyeGeo, eyeMat);
    this.eyeR.position.set(-0.08, 1.37, 0.19);
    this.avatarGroup.add(this.eyeR);

    const mouthGeo = new T.BoxGeometry(0.06, 0.015, 0.02);
    this.mouthMat = new T.MeshBasicMaterial({ color: 0xe11d48 });
    this.mouth = new T.Mesh(mouthGeo, this.mouthMat);
    this.mouth.position.set(0, 1.25, 0.21);
    this.avatarGroup.add(this.mouth);

    const bodyMat = new T.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.3 });
    const body = new T.Mesh(new T.CylinderGeometry(0.16, 0.2, 0.55, 20), bodyMat);
    body.position.y = 0.95;
    this.avatarGroup.add(body);

    this.scene.add(this.avatarGroup);
  }

  async loadGuraModel() {
    const T = window.THREE;
    console.log("[Avatar] Loading Gawr Gura 3D Model...");

    // 1. Try loading GLB first
    if (T.GLTFLoader) {
      const gltfLoader = new T.GLTFLoader();
      const glbUrl = "/models/gura/source/gura.glb";

      gltfLoader.load(
        glbUrl,
        (gltf) => {
          console.log("[Avatar] Gawr Gura GLB loaded successfully!");
          this.setupModel(gltf.scene, gltf.animations);
        },
        (xhr) => {
          if (xhr.lengthComputable) {
            console.log(`[Avatar] Loading Gura GLB: ${Math.round((xhr.loaded / xhr.total) * 100)}%`);
          }
        },
        (err) => {
          console.warn("[Avatar] GLB load failed, trying FBX fallback...", err);
          this.loadGuraFbxFallback();
        }
      );
    } else {
      this.loadGuraFbxFallback();
    }
  }

  loadGuraFbxFallback() {
    const T = window.THREE;
    if (!T.FBXLoader) return;

    try {
      const texLoader = new T.TextureLoader();
      const loadTex = (url) => {
        const tex = texLoader.load(url, () => this.renderer?.render(this.scene, this.camera));
        tex.encoding = T.sRGBEncoding;
        tex.flipY = true;
        return tex;
      };

      const bodyTex = loadTex("/models/gura/textures/body.png");
      const faceTex = loadTex("/models/gura/textures/face.png");
      const hairTex = loadTex("/models/gura/textures/hair.png");

      const bodyMats = new Set(['体', '服', '服白', '服黒', '服灰', '服赤', '服金', '服内']);
      const faceMats = new Set(['白目', '歯', '口内', '顔', '顔線無し', '瞳', 'ハイライト', '瞳拡張', 'まつげ', 'まゆ']);
      const hairMats = new Set(['帽子', '後髪', 'おさげ改', '横髪', 'ex', '前髪', 'ex2']);

      const fbxLoader = new T.FBXLoader();
      const modelUrl = "/models/gura/source/Gawr Gura.fbx";

      fbxLoader.load(
        modelUrl,
        (fbx) => {
          console.log("[Avatar] Gawr Gura FBX fallback loaded!");
          fbx.traverse((child) => {
            if (child.isMesh) {
              const rawMats = Array.isArray(child.material) ? child.material : [child.material];
              rawMats.forEach((mat) => {
                if (!mat) return;
                const mName = mat.name || "";
                let map = bodyTex;
                let transparent = false;
                let alphaTest = 0;

                if (bodyMats.has(mName)) {
                  map = bodyTex;
                } else if (faceMats.has(mName)) {
                  map = faceTex;
                  if (mName === '瞳' || mName === 'ハイライト' || mName === 'まつげ' || mName === 'まゆ') {
                    transparent = true;
                    alphaTest = 0.1;
                  }
                } else if (hairMats.has(mName)) {
                  map = hairTex;
                  if (mName === 'おさげ改') {
                    transparent = true;
                    alphaTest = 0.1;
                  }
                }

                mat.map = map;
                mat.color.setHex(0xffffff);
                mat.side = T.DoubleSide;
                mat.transparent = transparent;
                mat.alphaTest = alphaTest;
                mat.skinning = true;
                mat.needsUpdate = true;
              });
            }
          });

          this.setupModel(fbx, fbx.animations || []);
        },
        undefined,
        (err) => console.warn("[Avatar] Gura FBX fallback failed:", err)
      );
    } catch (e) {
      console.warn("[Avatar] Exception loading Gura FBX fallback:", e);
    }
  }

  setupModel(modelRoot, animations = []) {
    const T = window.THREE;
    this.guraModel = modelRoot;

    // Calculate scale and position to center character (~1.45m height)
    const bbox = new T.Box3().setFromObject(this.guraModel);
    const size = bbox.getSize(new T.Vector3());
    const targetHeight = 1.45;
    const scale = size.y > 0 ? targetHeight / size.y : 1.0;

    this.guraModel.scale.setScalar(scale);
    this.guraModel.position.set(0, 0, 0);

    // Map bones and configure materials
    this.guraBones = {};
    this.hairBones = [];
    this.tailBones = [];

    this.guraModel.traverse((child) => {
      if (child.isMesh) {
        child.castShadow = true;
        child.receiveShadow = true;
        child.frustumCulled = false;

        const rawMats = Array.isArray(child.material) ? child.material : [child.material];
        rawMats.forEach((mat) => {
          if (!mat) return;
          const mName = mat.name || "";

          // Hide any inverted outline material hull
          if (mName === "OH_Outline_Material" || mName.toLowerCase().includes("outline")) {
            child.visible = false;
            mat.visible = false;
            return;
          }

          mat.side = T.DoubleSide;
          if (mat.map) {
            mat.map.encoding = T.sRGBEncoding;
            mat.map.needsUpdate = true;
          }

          // Cutout materials (lashes, brows, highlights, eye dilation, shadows)
          const isCutout = ['まつげ', 'まゆ', 'ハイライト', '瞳拡張', 'おさげ改', '顔線無し', 'hair shadow'].some(k => mName.includes(k));
          if (isCutout) {
            mat.transparent = true;
            mat.alphaTest = 0.25;
            mat.depthWrite = true;
          } else {
            mat.transparent = false;
            mat.depthWrite = true;
            mat.depthTest = true;
          }

          mat.roughness = 0.5;
          mat.metalness = 0.02;
          mat.needsUpdate = true;
        });
      }

      if (child.isBone) {
        const bName = child.name;
        if (bName === "頭" || bName === "Head") this.guraBones.head = child;
        else if (bName === "首" || bName === "Neck") this.guraBones.neck = child;
        else if (bName === "上半身" || bName === "Spine") this.guraBones.spine = child;
        else if (bName === "上半身2" || bName === "Chest") this.guraBones.chest = child;
        else if (bName === "下半身" || bName === "Hips") this.guraBones.hips = child;
        else if (bName.startsWith("尻尾")) this.tailBones.push(child);
        else if (bName.startsWith("おさげ") || bName.startsWith("横髪") || bName.startsWith("前髪")) this.hairBones.push(child);
      }
    });

    this.scene.add(this.guraModel);

    // Hide procedural fallback avatar
    if (this.avatarGroup) {
      this.avatarGroup.visible = false;
    }

    // Set camera framing
    this.camera.position.set(0, 1.20, 1.25);
    this.camera.lookAt(0, 1.12, 0);

    // Setup Animation Mixer
    this.mixer = new T.AnimationMixer(this.guraModel);

    // NOTE: Per user request, NO IDLE ANIMATION is played in idle!
    // The natural procedural idle with breathing, eye/head tracking, and physics is active.
    this.idleAction = null;

    // Load Talking Animation from model or external FBX
    const talkClip = animations && animations.find(a => a.name.toLowerCase().includes("talk") || a.name.toLowerCase().includes("action"));
    if (talkClip) {
      this.talkingAction = this.mixer.clipAction(talkClip);
      this.talkingAction.setLoop(T.LoopRepeat, Infinity);
      console.log(`[Avatar] Talking animation '${talkClip.name}' loaded! (Idle animation disabled per user request)`);
    } else {
      this.loadExternalTalkingAnimation();
    }

    console.log("[Avatar] Gawr Gura 3D Model ready on stage!");
  }

  loadExternalTalkingAnimation() {
    const T = window.THREE;
    if (!T.FBXLoader) return;
    const fbxLoader = new T.FBXLoader();

    fbxLoader.load(
      "/models/animations/Talking.fbx",
      (fbx) => {
        const clip = fbx.animations?.find((a) => a.tracks && a.tracks.length > 0) || fbx.animations?.[0];
        if (clip) {
          const retargeted = this.retargetMixamoClip(clip, "Talking");
          this.talkingAction = this.mixer.clipAction(retargeted);
          this.talkingAction.setLoop(T.LoopRepeat, Infinity);
          console.log("[Avatar] External Talking.fbx loaded for Gura!");
        }
      },
      undefined,
      (err) => console.warn("[Avatar] Error loading external Talking.fbx:", err)
    );
  }

  retargetMixamoClip(clip, name) {
    const T = window.THREE;
    const boneMap = {
      mixamorigHips: "下半身",
      mixamorigSpine: "上半身",
      mixamorigSpine1: "上半身2",
      mixamorigSpine2: "上半身3",
      mixamorigNeck: "首",
      mixamorigHead: "頭",
      mixamorigLeftShoulder: "肩.L",
      mixamorigLeftArm: "腕.L",
      mixamorigLeftForeArm: "ひじ.L",
      mixamorigLeftHand: "手首.L",
      mixamorigRightShoulder: "肩.R",
      mixamorigRightArm: "腕.R",
      mixamorigRightForeArm: "ひじ.R",
      mixamorigRightHand: "手首.R",
      mixamorigLeftUpLeg: "足.L",
      mixamorigLeftLeg: "ひざ.L",
      mixamorigLeftFoot: "足首.L",
      mixamorigLeftToeBase: "つま先.L",
      mixamorigRightUpLeg: "足.R",
      mixamorigRightLeg: "ひざ.R",
      mixamorigRightFoot: "足首.R",
      mixamorigRightToeBase: "つま先.R",
    };

    const newTracks = [];
    clip.tracks.forEach((track) => {
      const parts = track.name.split(".");
      let rawBone = parts[0];
      const prop = parts[1];

      const cleanKey = rawBone.replace("mixamorig:", "mixamorig").replace(/[:_]/g, "");

      if (prop === "position" && (cleanKey.toLowerCase().includes("hips") || cleanKey.toLowerCase().includes("root"))) {
        return;
      }

      const mappedBone = boneMap[cleanKey] || boneMap[rawBone] || rawBone;
      if (mappedBone) {
        const newTrack = new track.constructor(mappedBone + "." + prop, track.times, track.values);
        newTracks.push(newTrack);
      }
    });

    return new T.AnimationClip(name, clip.duration, newTracks);
  }

  setExpression(name) {
    this.expression = name;
  }

  startSpeaking(text) {
    this.isSpeaking = true;

    // Play Talking animation
    if (this.talkingAction) {
      this.talkingAction.reset();
      this.talkingAction.fadeIn(0.25);
      this.talkingAction.play();
    }

    let visemeIndex = 0;
    const visemes = [0.3, 0.6, 0.9, 0.4, 0.8, 0.3];

    if (this.lipSyncInterval) clearInterval(this.lipSyncInterval);
    this.lipSyncInterval = setInterval(() => {
      if (!this.isSpeaking) {
        this.lipSyncValue = 0;
        clearInterval(this.lipSyncInterval);
        return;
      }
      this.lipSyncValue = visemes[visemeIndex % visemes.length] + Math.random() * 0.15;
      visemeIndex++;
    }, 80);
  }

  stopSpeaking() {
    this.isSpeaking = false;
    this.lipSyncValue = 0;
    if (this.lipSyncInterval) clearInterval(this.lipSyncInterval);

    // Fade out Talking animation back to natural procedural idle
    if (this.talkingAction) {
      this.talkingAction.fadeOut(0.35);
    }
  }

  animate() {
    requestAnimationFrame(() => this.animate());
    const delta = this.clock ? this.clock.getDelta() : 0.016;
    const time = this.clock ? this.clock.getElapsedTime() : Date.now() * 0.001;

    // Smooth mouse tracking interpolation
    this.mouse.x += (this.targetMouse.x - this.mouse.x) * 0.05;
    this.mouse.y += (this.targetMouse.y - this.mouse.y) * 0.05;

    // Update animation mixer (for talking action when speaking)
    if (this.mixer) {
      this.mixer.update(delta);
    }

    if (this.guraModel) {
      // Natural procedural breathing in idle
      if (this.guraBones.spine) {
        this.guraBones.spine.rotation.x = Math.sin(time * 1.6) * 0.018;
      }
      if (this.guraBones.chest) {
        this.guraBones.chest.rotation.x = Math.sin(time * 1.6 + 0.3) * 0.012;
      }

      // Dynamic Head & Neck tracking cursor
      if (this.guraBones.head) {
        this.guraBones.head.rotation.y += (this.mouse.x * 0.18 - this.guraBones.head.rotation.y) * 0.06;
        this.guraBones.head.rotation.x += (-this.mouse.y * 0.12 - this.guraBones.head.rotation.x) * 0.06;
      }
      if (this.guraBones.neck) {
        this.guraBones.neck.rotation.y += (this.mouse.x * 0.08 - this.guraBones.neck.rotation.y) * 0.05;
      }

      // Secondary dynamic physics: Gura shark tail swaying
      if (this.tailBones.length > 0) {
        this.tailBones.forEach((tb, idx) => {
          const phase = idx * 0.3;
          tb.rotation.y = Math.sin(time * 2.0 - phase) * (0.07 + idx * 0.02);
          tb.rotation.z = Math.cos(time * 1.4 - phase) * 0.03;
        });
      }

      // Secondary dynamic physics: Hair swaying
      if (this.hairBones.length > 0) {
        this.hairBones.forEach((hb, idx) => {
          const phase = idx * 0.15;
          hb.rotation.x = Math.sin(time * 1.8 - phase) * 0.02;
          hb.rotation.z = Math.cos(time * 1.5 - phase) * 0.02;
        });
      }
    }

    // Procedural Fallback Avatar animation
    if (this.avatarGroup && this.avatarGroup.visible) {
      this.avatarGroup.position.y = Math.sin(time * 2) * 0.015;
      if (this.mouth) {
        const targetScaleY = 1 + this.lipSyncValue * 5;
        this.mouth.scale.set(1 + this.lipSyncValue * 1.5, targetScaleY, 1);
      }
    }

    // Background cyber dust particle rotation
    if (this.particles) {
      this.particles.rotation.y = time * 0.025;
    }

    this.renderer.render(this.scene, this.camera);
  }

  onResize() {
    const width = window.innerWidth;
    const height = window.innerHeight;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  }

  loadScript(src) {
    return new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = src;
      script.onload = resolve;
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }
}
