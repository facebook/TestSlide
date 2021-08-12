- Create a new release tag by running:
    - `./release.sh $new_version`
- https://github.com/facebook/TestSlide/actions
    - Check if main build is OK.
- https://readthedocs.org/projects/testslide/
    - Trigger bulid for
        - new version
        - main
    - Admin > Versions: make new version the default
- Build & publish
    - `make twine`

- After the above (should have changed the version on package.json), publish a
  new version of testslide-snippets VSCode extension
    - You'll have to be logged in to the publisher `vsce login testslide-snippets`
    - run: `vsce publish`
