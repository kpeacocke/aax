# AWX devel UI repair

The original devel bundle was built with `headless=True`, so its API runs but
`/` fails with `TemplateDoesNotExist: index_awx.html`. This derivative preserves
that exact backend and adds the official standalone Ansible UI, pinned to the
upstream webpack upgrade commit `b512f07205f2be38d29dc245e955e66e64248ae3`.
The current UI main branch uses a different platform build layout.
This devel backend resolves templates under `awx/ui/build/awx`; the repository's
separate stable 24.6.1 Dockerfile uses `ui_next`, which is not this base image.
The workflow loads the actual derivative image's Django template to verify this.

The workflow verifies Django can load the template and compiled JavaScript is
present before publishing `aax-awx:ui-<commit>`. Set `DEVEL_AWX_IMAGE_TAG` to that
tag to repair web and task containers without changing the rest of the bundle.
Database migrations, credentials, and application settings are unchanged by
this image layer. Browser login and application behavior still require live
verification; asset presence is not proof of complete UI/API compatibility.

The devel API rejects the pinned UI's `notification_admin_role` organization
filter. The build applies a narrow compatibility patch: only that exact HTTP 400
response becomes an empty result for the optional notification-tab probe. Other
validation errors, authentication failures, authorization failures, and server
errors still propagate. This hides the unsupported notification capability and
does not grant permissions or bypass the API's access checks. Node regression
tests cover those boundaries, and pull requests build the complete UI image.
