export const demoPage = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>DropBy Discovery Demo</title>
  <style>
    :root { color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; background: radial-gradient(circle at top, #23334a, #090c12 55%); color: #f7f8fb; }
    main { width: min(760px, calc(100% - 32px)); margin: 0 auto; padding: 56px 0; }
    .eyebrow { color: #8fffc1; text-transform: uppercase; letter-spacing: .15em; font-weight: 800; font-size: 12px; }
    h1 { font-size: clamp(36px, 8vw, 68px); margin: 8px 0 10px; letter-spacing: -.055em; }
    .lede { color: #aeb8c7; max-width: 590px; font-size: 18px; line-height: 1.55; }
    .panel { margin-top: 32px; padding: 22px; border: 1px solid #2b3544; border-radius: 22px; background: rgba(18,23,32,.86); box-shadow: 0 18px 60px #0008; }
    .status { display: flex; align-items: center; gap: 9px; color: #c8d0dc; font-size: 14px; }
    .dot { width: 9px; height: 9px; border-radius: 50%; background: #ffbc52; box-shadow: 0 0 16px #ffbc52; }
    .dot.live { background: #5cff9d; box-shadow: 0 0 16px #5cff9d; }
    .buttons { display: grid; grid-template-columns: repeat(auto-fit,minmax(130px,1fr)); gap: 10px; margin: 20px 0; }
    button { border: 0; border-radius: 14px; padding: 13px 14px; background: #293548; color: white; font: inherit; font-weight: 750; cursor: pointer; }
    button:hover { transform: translateY(-1px); background: #35455e; }
    button.primary { background: #65f49e; color: #07130c; }
    pre { min-height: 230px; overflow: auto; padding: 18px; border-radius: 14px; background: #080b10; color: #b8f7d1; line-height: 1.45; white-space: pre-wrap; }
    small { color: #7e8999; }
  </style>
</head>
<body>
  <main>
    <div class="eyebrow">Docker-free developer mode</div>
    <h1>Find the Drop.</h1>
    <p class="lede">Move the simulated user toward a hidden Melbourne Drop. Notice how the API progressively reveals information instead of sending every offer immediately.</p>
    <section class="panel">
      <div class="status"><span id="dot" class="dot"></span><span id="status">Creating demo explorer…</span></div>
      <div class="buttons">
        <button onclick="move('detect')">500m · Detect</button>
        <button onclick="move('partial')">150m · Reveal</button>
        <button onclick="move('full')">50m · Discover</button>
        <button class="primary" onclick="startSquad()">Start squad</button>
      </div>
      <pre id="output">Waiting for demo session…</pre>
      <small>Demo data is held in memory and resets when the server restarts.</small>
    </section>
  </main>
  <script src="/socket.io/socket.io.js"></script>
  <script>
    let token = "";
    const output = document.getElementById("output");
    const status = document.getElementById("status");
    const dot = document.getElementById("dot");
    const positions = {
      detect: [-37.8074, 144.9674],
      partial: [-37.81055, 144.9674],
      full: [-37.81145, 144.9674]
    };
    const show = (label, value) => output.textContent = label + "\n\n" + JSON.stringify(value, null, 2);
    async function request(path, options = {}) {
      const response = await fetch(path, {
        ...options,
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: "Bearer " + token } : {}), ...(options.headers || {}) }
      });
      const body = await response.json();
      if (!response.ok) throw body;
      return body;
    }
    async function boot() {
      try {
        const session = await request("/v1/auth/register", {
          method: "POST",
          body: JSON.stringify({ email: "demo-" + Date.now() + "@dropby.local", password: "dropby-demo-password", displayName: "Demo Explorer" })
        });
        token = session.accessToken;
        const socket = io({ auth: { token } });
        socket.on("connect", () => { dot.classList.add("live"); status.textContent = "Demo API and realtime connection ready"; });
        socket.on("squad.updated", squad => show("LIVE EVENT · squad.updated", squad));
        show("SESSION READY", { user: session.user, next: "Choose a distance above" });
      } catch (error) { show("STARTUP ERROR", error); }
    }
    async function move(stage) {
      try {
        const [latitude, longitude] = positions[stage];
        const result = await request("/v1/drops/nearby?latitude=" + latitude + "&longitude=" + longitude);
        show(stage.toUpperCase() + " STAGE", result);
      } catch (error) { show("ERROR", error); }
    }
    async function startSquad() {
      try {
        await move("full");
        const result = await request("/v1/groups", {
          method: "POST",
          body: JSON.stringify({ dropId: "10000000-0000-4000-8000-000000000001", openToNearby: true })
        });
        show("SQUAD CREATED", result);
      } catch (error) { show("ERROR", error); }
    }
    boot();
  </script>
</body>
</html>`;
