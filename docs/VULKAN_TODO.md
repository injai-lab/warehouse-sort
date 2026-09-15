# Deferred: Vulkan video rendering

Observed: `RuntimeError: vk::createInstanceUnique: ErrorIncompatibleDriver`.
SAPIEN reported missing Vulkan external-memory/semaphore extensions and unavailable NVIDIA
rendering support in the container. Local GL/GLib libraries fix OpenCV import only.

Future task: inspect container graphics-driver exposure with its administrator, then test
GPU rendering and MP4 capture. No system driver changes or video retries are part of this
full headless training run; preserve the working state environment.
