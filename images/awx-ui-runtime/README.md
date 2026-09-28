# AWX devel UI repair

The original devel bundle was built with `headless=True`, so its API runs but
`/` fails with `TemplateDoesNotExist: index_awx.html`. This derivative preserves
that exact backend and adds the official standalone Ansible UI, pinned to the
upstream webpack upgrade commit `b512f07205f2be38d29dc245e955e66e64248ae3`.
The current UI main branch uses a different platform build layout.

The workflow verifies Django can load the template and compiled JavaScript is
present before publishing `aax-awx:ui-<commit>`. Set `DEVEL_AWX_IMAGE_TAG` to that
tag to repair web and task containers without changing the rest of the bundle.
Database migrations, credentials, and application settings are unchanged by
this image layer. Browser login and application behavior still require live
verification; asset presence is not proof of complete UI/API compatibility.
