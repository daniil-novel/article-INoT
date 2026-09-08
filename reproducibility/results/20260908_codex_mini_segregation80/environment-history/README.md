# Pre-generation environment history

Image-v1 adds the nine missing libraries but has a protobuf/e2b import conflict.
Image-v2 pins e2b 1.0.5 and yields 77/80 passing gold controls.
Image-v3 restores the documented reference-library contracts and yields 80/80.
All images are based on the unchanged bcb-heldout200:v3 image.

The intermediate controls-v3 pair was diagnostic only: its negative run recorded
the then-current image-v3 requirements file while still invoking image-v2. The
actual image ID and pip freeze remain recorded. That pair cannot supply a valid
control gate and was not used for inference. The full controls-v4 pair uses the
same final requirements, image and runtime package identities in both runs and
passes the strict gate audit. No candidate generation precedes this final gate.

The image-v2 requirements bytes are reconstructed from the preceding committed
file plus the recorded e2b pin and match its gold-run requirements SHA-256.
Build logs, each exact requirements file and actual package freezes are retained;
no claim of bit-for-bit Docker image reconstruction from a live package index
is made.
