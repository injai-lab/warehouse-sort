# Deferred: Vulkan video rendering

Observed: `RuntimeError: vk::createInstanceUnique: ErrorIncompatibleDriver`.
SAPIEN reported missing Vulkan external-memory/semaphore extensions and unavailable NVIDIA
rendering support in the container. Local GL/GLib libraries fix OpenCV import only.

Future task: inspect container graphics-driver exposure with its administrator, then test
GPU rendering and MP4 capture. No system driver changes or video retries are part of this
full headless training run; preserve the working state environment.

## 2026-09-17 live viewing

Rendering still fails with ErrorIncompatibleDriver; container advertises compute,utility only.
No available X11/Wayland/VNC/RDP desktop was found. No driver changes made.
A loopback browser viewer now renders live PhysX link/actor poses using PC WebGL and the
installed Panda GLB assets. This is a separate visualization, not restored SAPIEN rendering.
See [실시간 관람 안내](LIVE_VIEWER_KO.md).
