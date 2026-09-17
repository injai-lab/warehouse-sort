# Live browser viewer validation

- Vulkan recheck: `vk::createInstanceUnique: ErrorIncompatibleDriver` remains.
- No usable X11/Wayland/VNC/RDP desktop found from this account. NVIDIA capabilities: compute,utility.
- Implemented live PhysX pose streaming to a PC WebGL scene using local Panda GLB assets.
- Kept state observations, original best EMA SHA256, DDPM 100, action chunk 8, FrameStack 2, one V100.
- Standard-library HTTP server binds only 127.0.0.1:8765. No public tunnel or firewall change.
- Tested with Chromium/Playwright: meshes loaded, policy advanced, pause held state, reset returned to step 0, full episode stopped at step 200, no JavaScript exceptions.
- Validated /proc/net/tcp listener = 0100007F:223D; non-allowlisted file paths return 404; control without per-process key returns 403.
- Verified SIGINT shutdown removes PID file and all GPUs return to their initial 4 MiB memory usage.
- Service restarted paused for the user. VS Code's authenticated private forwarding still must be opened from the user's desktop.
- Browser test screenshots and logs remain in ignored runs/. No training or checkpoint modifications.
- Project .venv and system packages/drivers unchanged. Three.js cached locally; browser test libraries extracted under .cache/browser-test-libs, Chromium/Playwright in user cache.
- Browser test initially failed on missing shared libraries; resolved using project-local extraction. Some stale apt update URLs returned 404; downloaded explicit noble base versions instead.

[Connection, start/stop, file map, limitations, and administrator requirements](../docs/LIVE_VIEWER_KO.md).

## Blank-screen recovery

User screenshot confirmed successful private-tunnel HTML access but initialization remained stuck.
Client cause not established from screenshot alone. Removed coupling between WebGL startup and
state/control polling; added import timeout, visible initialization errors, and a Canvas live-pose
fallback for blocked modules, failed WebGL, or mesh-load errors. Tested normal WebGL, disabled
WebGL (including real policy movement), and blocked module download: all had usable state and
controls, no uncaught JS exceptions. Refreshed HTML/JS are served without a simulator restart.

## Tunnel timeout follow-up

User screenshot showed a 20-second module timeout and 10-second state-request timeout (not a confirmed WebGL failure). Local endpoints responded in milliseconds.
Bundled JS into inline HTML, enabled gzip + HTTP/1.1 persistent connections, expanded accept backlog, sequenced mesh downloads, and slowed idle polling.
Measured initial HTML+bundle 153,792 compressed bytes; initial state 1,894 bytes. Public exposure unchanged.
The browser test emulates 250 ms latency and 128,000 bytes/s download and checks state/control while loading the actual robot meshes.
Result: slow-network test loaded full WebGL robot meshes, advanced the real policy, paused and reset successfully; zero separate JS requests and zero JS exceptions. WebGL-disabled fallback also passed. Server left ready/paused at step 0.
